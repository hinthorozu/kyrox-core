import json
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.infrastructure.persistence.models import AuditLogModel
from app.modules.identity.application.authentication.password_change import (
    ChangePasswordCommand,
    ChangePasswordUseCase,
    PasswordChangeAuditPort,
)
from app.modules.identity.application.authentication.revoke_all_user_sessions import (
    RevokeAllUserSessionsUseCase,
)
from app.modules.identity.application.organization.policy import OrganizationNamingPolicy
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authentication.value_objects.security.password_hash import (
    PasswordHash,
)
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.infrastructure.authentication.persistence.models import (
    RefreshTokenModel,
    SessionModel,
)
from app.modules.identity.infrastructure.authentication.repositories import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.authentication.security import Argon2idPasswordHasher
from app.modules.identity.infrastructure.organization.repositories import (
    SqlAlchemyOrganizationRepository,
)
from app.modules.identity.infrastructure.persistence.models import UserModel

_OLD_PASSWORD = "old password value 123"
_NEW_PASSWORD = "new password value 456"


@dataclass
class MutableClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


class FailingPasswordChangeAuditPort(PasswordChangeAuditPort):
    def record_password_change(
        self,
        *,
        organization_id: uuid.UUID | None,
        user_id: uuid.UUID,
        sessions_revoked: int,
        refresh_tokens_revoked: int,
    ) -> None:
        raise RuntimeError("forced password change audit failure")


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


def _seed_active_account(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    clock = MutableClock(datetime.now(UTC))
    naming = OrganizationNamingPolicy()
    organization_id = OrganizationId(uuid.uuid4())
    organization = SqlAlchemyOrganizationRepository(db_session, clock).add(
        Organization(
            id=organization_id,
            name=naming.normalize_name("Password Change Organization"),
            slug=naming.normalize_slug(f"password-change-{organization_id.value.hex[:12]}"),
            status=OrganizationStatus.ACTIVE,
            created_at=clock.now(),
            updated_at=clock.now(),
        )
    )
    user_id = UserId(uuid.uuid4())
    user = SqlAlchemyUserRepository(db_session, clock).add(
        User(
            id=user_id,
            email=Email.create("password.change@example.com"),
            password_hash=Argon2idPasswordHasher().hash(_OLD_PASSWORD),
            status=UserStatus.ACTIVE,
            created_at=clock.now(),
            updated_at=clock.now(),
            organization_id=organization.id.value,
            is_super_admin=False,
        )
    )
    db_session.commit()
    return organization.id.value, user.id.value


def _client(db_session: Session) -> tuple[object, TestClient]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    return app, TestClient(app)


def test_password_change_requires_bearer_authentication(db_session: Session) -> None:
    _seed_active_account(db_session)
    app, client = _client(db_session)
    try:
        with client:
            response = client.post(
                "/api/v1/auth/password/change",
                json={
                    "current_password": _OLD_PASSWORD,
                    "new_password": _NEW_PASSWORD,
                },
            )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_password_change_rejects_wrong_current_weak_and_same_password_without_revocation(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, user_id = _seed_active_account(db_session)
    app, client = _client(db_session)
    try:
        with client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": "password.change@example.com", "password": _OLD_PASSWORD},
            )
            assert login.status_code == 200, login.text
            access = login.json()["access_token"]
            refresh = login.json()["refresh_token"]
            headers = {"Authorization": f"Bearer {access}"}

            wrong = client.post(
                "/api/v1/auth/password/change",
                headers=headers,
                json={
                    "current_password": "wrong current secret",
                    "new_password": _NEW_PASSWORD,
                },
            )
            assert wrong.status_code == 400
            assert "wrong current secret" not in wrong.text
            assert "wrong current secret" not in caplog.text

            weak = client.post(
                "/api/v1/auth/password/change",
                headers=headers,
                json={
                    "current_password": _OLD_PASSWORD,
                    "new_password": "short",
                },
            )
            assert weak.status_code == 422
            assert "short" not in weak.text

            same = client.post(
                "/api/v1/auth/password/change",
                headers=headers,
                json={
                    "current_password": _OLD_PASSWORD,
                    "new_password": _OLD_PASSWORD,
                },
            )
            assert same.status_code == 422

            # Failed attempts must not invalidate the authenticated session.
            refresh_after_failures = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh},
            )
            assert refresh_after_failures.status_code == 200

        user_model = db_session.get(UserModel, user_id)
        assert user_model is not None and user_model.password_hash is not None
        assert Argon2idPasswordHasher().verify(
            _OLD_PASSWORD,
            PasswordHash(user_model.password_hash),
        )
    finally:
        app.dependency_overrides.clear()


def test_password_change_revokes_prior_credentials_and_allows_new_password_only(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    organization_id, user_id = _seed_active_account(db_session)
    app, client = _client(db_session)
    try:
        with client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": "password.change@example.com", "password": _OLD_PASSWORD},
            )
            assert login.status_code == 200, login.text
            access = login.json()["access_token"]
            refresh = login.json()["refresh_token"]
            headers = {"Authorization": f"Bearer {access}"}

            changed = client.post(
                "/api/v1/auth/password/change",
                headers=headers,
                json={
                    "current_password": _OLD_PASSWORD,
                    "new_password": _NEW_PASSWORD,
                },
            )
            assert changed.status_code == 200, changed.text
            assert _OLD_PASSWORD not in changed.text
            assert _NEW_PASSWORD not in changed.text
            assert _OLD_PASSWORD not in caplog.text
            assert _NEW_PASSWORD not in caplog.text

            # The successful change revokes the current access-token session too.
            stale_access = client.post(
                "/api/v1/auth/password/change",
                headers=headers,
                json={
                    "current_password": _NEW_PASSWORD,
                    "new_password": "third password value 789",
                },
            )
            assert stale_access.status_code == 401

            stale_refresh = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh},
            )
            assert stale_refresh.status_code == 401

            old_login = client.post(
                "/api/v1/auth/login",
                json={"email": "password.change@example.com", "password": _OLD_PASSWORD},
            )
            assert old_login.status_code == 401

            new_login = client.post(
                "/api/v1/auth/login",
                json={"email": "password.change@example.com", "password": _NEW_PASSWORD},
            )
            assert new_login.status_code == 200, new_login.text

        revoked_session = db_session.scalar(
            select(SessionModel).where(
                SessionModel.user_id == user_id,
                SessionModel.revoked_at.is_not(None),
            )
        )
        assert revoked_session is not None
        refresh_model = db_session.scalar(
            select(RefreshTokenModel).where(
                RefreshTokenModel.session_id == revoked_session.id,
                RefreshTokenModel.revoked_at.is_not(None),
            )
        )
        assert refresh_model is not None

        audit = db_session.scalar(
            select(AuditLogModel).where(
                AuditLogModel.organization_id == organization_id,
                AuditLogModel.user_id == user_id,
                AuditLogModel.action == "identity.password.change",
            )
        )
        assert audit is not None
        serialized_audit = json.dumps(
            {
                "old": audit.old_values,
                "new": audit.new_values,
                "metadata": audit.event_metadata,
            },
            sort_keys=True,
        )
        assert _OLD_PASSWORD not in serialized_audit
        assert _NEW_PASSWORD not in serialized_audit
    finally:
        app.dependency_overrides.clear()


def test_password_change_rolls_back_hash_and_revocation_if_audit_fails(
    db_session: Session,
) -> None:
    _, user_id = _seed_active_account(db_session)
    app, client = _client(db_session)
    try:
        with client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": "password.change@example.com", "password": _OLD_PASSWORD},
            )
            assert login.status_code == 200
        # The login transaction created a live session/refresh token.
    finally:
        app.dependency_overrides.clear()

    clock = MutableClock(datetime.now(UTC))
    user_repository = SqlAlchemyUserRepository(db_session, clock)
    use_case = ChangePasswordUseCase(
        user_repository=user_repository,
        password_hasher=Argon2idPasswordHasher(),
        revoke_all_user_sessions=RevokeAllUserSessionsUseCase(
            session_repository=SqlAlchemySessionRepository(db_session),
            refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session, clock),
            clock=clock,
        ),
        clock=clock,
        audit_port=FailingPasswordChangeAuditPort(),
    )

    with pytest.raises(RuntimeError, match="forced password change audit failure"):
        use_case.execute(
            ChangePasswordCommand(
                user_id=user_id,
                current_password=_OLD_PASSWORD,
                new_password=_NEW_PASSWORD,
            )
        )
    db_session.rollback()

    user_model = db_session.get(UserModel, user_id)
    assert user_model is not None and user_model.password_hash is not None
    hasher = Argon2idPasswordHasher()
    persisted_hash = PasswordHash(user_model.password_hash)
    assert hasher.verify(_OLD_PASSWORD, persisted_hash)
    assert not hasher.verify(_NEW_PASSWORD, persisted_hash)

    active_session = db_session.scalar(
        select(SessionModel).where(
            SessionModel.user_id == user_id,
            SessionModel.revoked_at.is_(None),
        )
    )
    assert active_session is not None
    active_refresh = db_session.scalar(
        select(RefreshTokenModel).where(
            RefreshTokenModel.session_id == active_session.id,
            RefreshTokenModel.revoked_at.is_(None),
        )
    )
    assert active_refresh is not None
