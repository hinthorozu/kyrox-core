import json
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.infrastructure.persistence.models import AuditLogModel
from app.modules.identity.application.authentication.id_generator import Uuid4IdGenerator
from app.modules.identity.application.authentication.identity_action_tokens import (
    IssueIdentityActionToken,
)
from app.modules.identity.application.authentication.password_recovery import (
    ForgotPasswordCommand,
    ForgotPasswordUseCase,
    PasswordResetNotificationPort,
)
from app.modules.identity.application.organization.policy import OrganizationNamingPolicy
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.infrastructure.authentication.persistence.models import (
    RefreshTokenModel,
    SessionModel,
)
from app.modules.identity.infrastructure.authentication.persistence.models.identity_action_token import (
    IdentityActionTokenModel,
)
from app.modules.identity.infrastructure.authentication.repositories import (
    SqlAlchemyIdentityActionTokenRepository,
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.authentication.security import Argon2idPasswordHasher
from app.modules.identity.infrastructure.authentication.security.identity_action_token_service import (
    IdentityActionTokenService,
)
from app.modules.identity.infrastructure.organization.repositories import (
    SqlAlchemyOrganizationRepository,
)
from app.modules.notifications.infrastructure.persistence.models import PlatformNotificationModel

_OLD_PASSWORD = "old password value 123"
_NEW_PASSWORD = "new password value 456"


@dataclass
class MutableClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


class RecordingResetNotificationPort(PasswordResetNotificationPort):
    def __init__(self) -> None:
        self.token_ids: list[IdentityActionTokenId] = []

    def enqueue_password_reset(
        self,
        *,
        recipient: str,
        user_id: UserId,
        token_id: IdentityActionTokenId,
    ) -> bool:
        self.token_ids.append(token_id)
        return True


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_active_account(
    db_session: Session,
    *,
    email: str = "recovery@example.com",
) -> tuple[uuid.UUID, uuid.UUID]:
    now = datetime.now(UTC)
    clock = MutableClock(now)
    ids = Uuid4IdGenerator()
    naming = OrganizationNamingPolicy()
    organization_id = OrganizationId(ids.generate_uuid())
    organization = SqlAlchemyOrganizationRepository(db_session, clock).add(
        Organization(
            id=organization_id,
            name=naming.normalize_name("Recovery Organization"),
            slug=naming.normalize_slug(f"recovery-{organization_id.value.hex[:12]}"),
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    user_id = UserId(ids.generate_uuid())
    user = SqlAlchemyUserRepository(db_session, clock).add(
        User(
            id=user_id,
            email=Email.create(email),
            password_hash=Argon2idPasswordHasher().hash(_OLD_PASSWORD),
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            organization_id=organization.id.value,
            is_super_admin=False,
        )
    )
    db_session.commit()
    return organization.id.value, user.id.value


def test_forgot_password_cooldown_and_supersession(db_session: Session) -> None:
    _, user_id = _seed_active_account(db_session)
    clock = MutableClock(datetime.now(UTC))
    token_repository = SqlAlchemyIdentityActionTokenRepository(db_session)
    token_service = IdentityActionTokenService(settings.CORE_IDENTITY_ACTION_TOKEN_SECRET_KEY)
    issue = IssueIdentityActionToken(
        repository=token_repository,
        token_service=token_service,
        clock=clock,
        id_generator=Uuid4IdGenerator(),
    )
    notification = RecordingResetNotificationPort()
    use_case = ForgotPasswordUseCase(
        user_repository=SqlAlchemyUserRepository(db_session, clock),
        organization_repository=SqlAlchemyOrganizationRepository(db_session, clock),
        identity_action_token_repository=token_repository,
        issue_identity_action_token=issue,
        notification_port=notification,
        clock=clock,
        token_ttl=timedelta(minutes=60),
        resend_cooldown=timedelta(seconds=60),
    )

    first = use_case.execute(ForgotPasswordCommand(email="RECOVERY@example.com"))
    second = use_case.execute(ForgotPasswordCommand(email="recovery@example.com"))
    assert first.notification_queued is True
    assert second.notification_queued is False
    assert len(notification.token_ids) == 1

    first_token = token_repository.get_by_id(notification.token_ids[0])
    assert first_token is not None and first_token.invalidated_at is None

    clock.current += timedelta(seconds=61)
    third = use_case.execute(ForgotPasswordCommand(email="recovery@example.com"))
    assert third.notification_queued is True
    assert len(notification.token_ids) == 2
    first_token = token_repository.get_by_id(notification.token_ids[0])
    latest = token_repository.get_latest_for_user_purpose(
        UserId(user_id), IdentityActionTokenPurpose.PASSWORD_RESET
    )
    assert first_token is not None and first_token.invalidated_at is not None
    assert latest is not None and latest.id == notification.token_ids[1]


def test_forgot_password_api_is_enumeration_safe_and_persists_no_raw_token(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, user_id = _seed_active_account(db_session)
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            known = client.post(
                "/api/v1/auth/password/forgot",
                json={"email": "recovery@example.com"},
            )
            unknown = client.post(
                "/api/v1/auth/password/forgot",
                json={"email": "unknown@example.com"},
            )
        assert known.status_code == unknown.status_code == 202
        assert known.json() == unknown.json()

        token = db_session.scalar(
            select(IdentityActionTokenModel).where(
                IdentityActionTokenModel.user_id == user_id,
                IdentityActionTokenModel.purpose == "password_reset",
            )
        )
        notification = db_session.scalar(
            select(PlatformNotificationModel).where(
                PlatformNotificationModel.recipient == "recovery@example.com"
            )
        )
        assert token is not None
        assert notification is not None
        raw_token = IdentityActionTokenService(
            settings.CORE_IDENTITY_ACTION_TOKEN_SECRET_KEY
        ).derive(IdentityActionTokenId(token.id))
        persisted = notification.body + json.dumps(notification.variables, sort_keys=True)
        assert raw_token not in persisted
        assert raw_token not in known.text
        assert raw_token not in caplog.text
        assert notification.variables == {"identity_action_token_id": str(token.id)}
    finally:
        app.dependency_overrides.clear()


def test_password_reset_revokes_prior_credentials_and_allows_only_new_password(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    organization_id, user_id = _seed_active_account(db_session)
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": "recovery@example.com", "password": _OLD_PASSWORD},
            )
            assert login.status_code == 200, login.text
            old_refresh = login.json()["refresh_token"]

            clock = MutableClock(datetime.now(UTC))
            token_repository = SqlAlchemyIdentityActionTokenRepository(db_session)
            issued = IssueIdentityActionToken(
                repository=token_repository,
                token_service=IdentityActionTokenService(
                    settings.CORE_IDENTITY_ACTION_TOKEN_SECRET_KEY
                ),
                clock=clock,
                id_generator=Uuid4IdGenerator(),
            ).execute(
                UserId(user_id),
                IdentityActionTokenPurpose.PASSWORD_RESET,
                timedelta(minutes=60),
                reconstructable=True,
            )
            db_session.commit()

            reset = client.post(
                "/api/v1/auth/password/reset",
                json={"token": issued.raw_token, "password": _NEW_PASSWORD},
            )
            assert reset.status_code == 200, reset.text
            assert issued.raw_token not in reset.text
            assert _NEW_PASSWORD not in reset.text
            assert issued.raw_token not in caplog.text
            assert _NEW_PASSWORD not in caplog.text

            replay = client.post(
                "/api/v1/auth/password/reset",
                json={"token": issued.raw_token, "password": _NEW_PASSWORD},
            )
            assert replay.status_code == 400

            old_login = client.post(
                "/api/v1/auth/login",
                json={"email": "recovery@example.com", "password": _OLD_PASSWORD},
            )
            assert old_login.status_code == 401

            new_login = client.post(
                "/api/v1/auth/login",
                json={"email": "recovery@example.com", "password": _NEW_PASSWORD},
            )
            assert new_login.status_code == 200, new_login.text

            old_refresh_response = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": old_refresh},
            )
            assert old_refresh_response.status_code == 401

        session = db_session.scalar(
            select(SessionModel).where(SessionModel.user_id == user_id)
        )
        refresh_token = db_session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id)
        )
        audit = db_session.scalar(
            select(AuditLogModel).where(
                AuditLogModel.organization_id == organization_id,
                AuditLogModel.user_id == user_id,
                AuditLogModel.action == "identity.password.reset",
            )
        )
        assert session is not None and session.revoked_at is not None
        assert refresh_token is not None and refresh_token.revoked_at is not None
        assert audit is not None
        serialized_audit = json.dumps(
            {
                "old": audit.old_values,
                "new": audit.new_values,
                "metadata": audit.event_metadata,
            },
            sort_keys=True,
        )
        assert issued.raw_token not in serialized_audit
        assert _NEW_PASSWORD not in serialized_audit
    finally:
        app.dependency_overrides.clear()


def test_password_reset_rejects_weak_password_without_consuming_token(
    db_session: Session,
) -> None:
    _, user_id = _seed_active_account(db_session)
    clock = MutableClock(datetime.now(UTC))
    repository = SqlAlchemyIdentityActionTokenRepository(db_session)
    issued = IssueIdentityActionToken(
        repository=repository,
        token_service=IdentityActionTokenService(
            settings.CORE_IDENTITY_ACTION_TOKEN_SECRET_KEY
        ),
        clock=clock,
        id_generator=Uuid4IdGenerator(),
    ).execute(
        UserId(user_id),
        IdentityActionTokenPurpose.PASSWORD_RESET,
        timedelta(minutes=60),
        reconstructable=True,
    )
    db_session.commit()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/password/reset",
                json={"token": issued.raw_token, "password": "short"},
            )
        assert response.status_code == 422
        token = repository.get_by_id(issued.token_id)
        assert token is not None and token.consumed_at is None
    finally:
        app.dependency_overrides.clear()
