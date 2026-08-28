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

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.infrastructure.persistence.models import AuditLogModel
from app.modules.identity.application.authentication.activation import (
    ActivationAuditPort,
    CompleteActivationCommand,
    CompleteActivationUseCase,
)
from app.modules.identity.application.authentication.id_generator import Uuid4IdGenerator
from app.modules.identity.application.authentication.identity_action_tokens import (
    ConsumeIdentityActionToken,
    IssueIdentityActionToken,
)
from app.modules.identity.application.organization.policy import OrganizationNamingPolicy
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.exceptions.authentication import (
    ActivationPasswordPolicyError,
    InvalidActivationTokenError,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId,
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
from app.modules.identity.infrastructure.organization.persistence.models.organization import (
    OrganizationModel,
)
from app.modules.identity.infrastructure.organization.repositories import (
    SqlAlchemyOrganizationRepository,
)
from app.modules.identity.infrastructure.persistence.models import UserModel

_TOKEN_SECRET = "a" * 48
_VALID_PASSWORD = "correct horse battery"


@dataclass
class MutableClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


class RecordingActivationAuditPort(ActivationAuditPort):
    def __init__(self) -> None:
        self.calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    def record_activation(self, *, organization_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.calls.append((organization_id, user_id))


class FailingActivationAuditPort(ActivationAuditPort):
    def record_activation(self, *, organization_id: uuid.UUID, user_id: uuid.UUID) -> None:
        raise RuntimeError("forced audit failure")


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


def _seed_pending_account(
    db_session: Session,
    *,
    clock: MutableClock,
    purpose: IdentityActionTokenPurpose = IdentityActionTokenPurpose.ACCOUNT_ACTIVATION,
    ttl: timedelta = timedelta(hours=24),
) -> tuple[uuid.UUID, uuid.UUID, str]:
    id_generator = Uuid4IdGenerator()
    naming_policy = OrganizationNamingPolicy()
    organization_id = OrganizationId(id_generator.generate_uuid())
    organization = SqlAlchemyOrganizationRepository(db_session, clock).add(
        Organization(
            id=organization_id,
            name=naming_policy.normalize_name("Activation Organization"),
            slug=naming_policy.normalize_slug(f"activation-{organization_id.value.hex[:12]}"),
            status=OrganizationStatus.PENDING_ACTIVATION,
            created_at=clock.now(),
            updated_at=clock.now(),
        )
    )

    user_id = UserId(id_generator.generate_uuid())
    user = SqlAlchemyUserRepository(db_session, clock).add(
        User(
            id=user_id,
            email=Email.create(f"activation-{user_id.value.hex[:8]}@example.com"),
            password_hash=None,
            status=UserStatus.INACTIVE,
            created_at=clock.now(),
            updated_at=clock.now(),
            organization_id=organization.id.value,
            is_super_admin=False,
        )
    )

    token_repository = SqlAlchemyIdentityActionTokenRepository(db_session)
    token_service = IdentityActionTokenService(_TOKEN_SECRET)
    issued = IssueIdentityActionToken(
        repository=token_repository,
        token_service=token_service,
        clock=clock,
        id_generator=id_generator,
    ).execute(
        user.id,
        purpose,
        ttl,
        reconstructable=True,
    )
    db_session.commit()
    return organization.id.value, user.id.value, issued.raw_token


def _build_use_case(
    db_session: Session,
    *,
    clock: MutableClock,
    audit_port: ActivationAuditPort,
) -> CompleteActivationUseCase:
    token_repository = SqlAlchemyIdentityActionTokenRepository(db_session)
    token_service = IdentityActionTokenService(_TOKEN_SECRET)
    return CompleteActivationUseCase(
        consume_identity_action_token=ConsumeIdentityActionToken(
            repository=token_repository,
            token_service=token_service,
            clock=clock,
        ),
        user_repository=SqlAlchemyUserRepository(db_session, clock),
        organization_repository=SqlAlchemyOrganizationRepository(db_session, clock),
        password_hasher=Argon2idPasswordHasher(),
        clock=clock,
        audit_port=audit_port,
    )


def test_activation_sets_password_activates_user_and_organization_and_consumes_token(
    db_session: Session,
) -> None:
    clock = MutableClock(datetime(2026, 8, 28, 18, 0, tzinfo=UTC))
    organization_id, user_id, raw_token = _seed_pending_account(
        db_session,
        clock=clock,
    )
    audit_port = RecordingActivationAuditPort()
    use_case = _build_use_case(db_session, clock=clock, audit_port=audit_port)

    result = use_case.execute(
        CompleteActivationCommand(token=raw_token, password=_VALID_PASSWORD)
    )

    user = SqlAlchemyUserRepository(db_session, clock).get_by_id(UserId(user_id))
    organization = SqlAlchemyOrganizationRepository(db_session, clock).get_by_id(
        OrganizationId(organization_id)
    )
    token = db_session.scalar(
        select(IdentityActionTokenModel).where(
            IdentityActionTokenModel.user_id == user_id,
            IdentityActionTokenModel.purpose == "account_activation",
        )
    )

    assert result.organization_id == organization_id
    assert result.user_id == user_id
    assert user is not None
    assert user.status is UserStatus.ACTIVE
    assert user.password_hash is not None
    assert Argon2idPasswordHasher().verify(_VALID_PASSWORD, user.password_hash)
    assert organization is not None
    assert organization.status is OrganizationStatus.ACTIVE
    assert token is not None
    assert token.consumed_at is not None
    assert audit_port.calls == [(organization_id, user_id)]


def test_activation_password_policy_failure_does_not_consume_token(
    db_session: Session,
) -> None:
    clock = MutableClock(datetime(2026, 8, 28, 18, 0, tzinfo=UTC))
    organization_id, user_id, raw_token = _seed_pending_account(
        db_session,
        clock=clock,
    )
    use_case = _build_use_case(
        db_session,
        clock=clock,
        audit_port=RecordingActivationAuditPort(),
    )

    with pytest.raises(ActivationPasswordPolicyError):
        use_case.execute(CompleteActivationCommand(token=raw_token, password="too-short"))

    token = db_session.scalar(
        select(IdentityActionTokenModel).where(
            IdentityActionTokenModel.user_id == user_id
        )
    )
    user = db_session.get(UserModel, user_id)
    organization = db_session.get(OrganizationModel, organization_id)
    assert token is not None and token.consumed_at is None
    assert user is not None and user.status == "inactive" and user.password_hash is None
    assert organization is not None and organization.status == "pending_activation"


def test_activation_rejects_replay_wrong_purpose_and_expired_tokens(
    db_session: Session,
) -> None:
    base_time = datetime(2026, 8, 28, 18, 0, tzinfo=UTC)

    replay_clock = MutableClock(base_time)
    _, _, replay_token = _seed_pending_account(db_session, clock=replay_clock)
    replay_use_case = _build_use_case(
        db_session,
        clock=replay_clock,
        audit_port=RecordingActivationAuditPort(),
    )
    replay_use_case.execute(
        CompleteActivationCommand(token=replay_token, password=_VALID_PASSWORD)
    )
    db_session.commit()
    with pytest.raises(InvalidActivationTokenError):
        replay_use_case.execute(
            CompleteActivationCommand(token=replay_token, password=_VALID_PASSWORD)
        )
    db_session.rollback()

    wrong_purpose_clock = MutableClock(base_time + timedelta(minutes=1))
    _, _, wrong_purpose_token = _seed_pending_account(
        db_session,
        clock=wrong_purpose_clock,
        purpose=IdentityActionTokenPurpose.PASSWORD_RESET,
    )
    wrong_purpose_use_case = _build_use_case(
        db_session,
        clock=wrong_purpose_clock,
        audit_port=RecordingActivationAuditPort(),
    )
    with pytest.raises(InvalidActivationTokenError):
        wrong_purpose_use_case.execute(
            CompleteActivationCommand(
                token=wrong_purpose_token,
                password=_VALID_PASSWORD,
            )
        )
    db_session.rollback()

    expired_clock = MutableClock(base_time + timedelta(minutes=2))
    _, _, expired_token = _seed_pending_account(
        db_session,
        clock=expired_clock,
        ttl=timedelta(seconds=1),
    )
    expired_clock.current += timedelta(seconds=2)
    expired_use_case = _build_use_case(
        db_session,
        clock=expired_clock,
        audit_port=RecordingActivationAuditPort(),
    )
    with pytest.raises(InvalidActivationTokenError):
        expired_use_case.execute(
            CompleteActivationCommand(token=expired_token, password=_VALID_PASSWORD)
        )


def test_activation_audit_failure_rolls_back_token_user_and_organization(
    db_session: Session,
) -> None:
    clock = MutableClock(datetime(2026, 8, 28, 18, 0, tzinfo=UTC))
    organization_id, user_id, raw_token = _seed_pending_account(
        db_session,
        clock=clock,
    )
    use_case = _build_use_case(
        db_session,
        clock=clock,
        audit_port=FailingActivationAuditPort(),
    )

    with pytest.raises(RuntimeError, match="forced audit failure"):
        use_case.execute(
            CompleteActivationCommand(token=raw_token, password=_VALID_PASSWORD)
        )
    db_session.rollback()

    token = db_session.scalar(
        select(IdentityActionTokenModel).where(
            IdentityActionTokenModel.user_id == user_id
        )
    )
    user = db_session.get(UserModel, user_id)
    organization = db_session.get(OrganizationModel, organization_id)
    assert token is not None and token.consumed_at is None
    assert user is not None and user.status == "inactive" and user.password_hash is None
    assert organization is not None and organization.status == "pending_activation"


def test_activation_api_is_single_use_audited_secret_safe_and_login_ready(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = MutableClock(datetime.now(UTC))
    organization_id, user_id, raw_token = _seed_pending_account(
        db_session,
        clock=clock,
    )
    user = db_session.get(UserModel, user_id)
    assert user is not None
    email = user.email

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
                "/api/v1/auth/activation/complete",
                json={"token": raw_token, "password": _VALID_PASSWORD},
            )
            assert response.status_code == 200, response.text
            assert response.json() == {
                "message": "Account activated. You can now sign in."
            }

            audit = db_session.scalar(
                select(AuditLogModel).where(
                    AuditLogModel.organization_id == organization_id,
                    AuditLogModel.user_id == user_id,
                    AuditLogModel.action == "identity.activation.complete",
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
            assert raw_token not in serialized_audit
            assert _VALID_PASSWORD not in serialized_audit
            assert raw_token not in response.text
            assert _VALID_PASSWORD not in response.text
            assert raw_token not in caplog.text
            assert _VALID_PASSWORD not in caplog.text

            replay = client.post(
                "/api/v1/auth/activation/complete",
                json={"token": raw_token, "password": _VALID_PASSWORD},
            )
            assert replay.status_code == 400
            assert replay.json() == {"detail": "Invalid or expired activation token"}

            login = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": _VALID_PASSWORD},
            )
            assert login.status_code == 200, login.text
            assert login.json()["access_token"]
            assert login.json()["refresh_token"]
    finally:
        app.dependency_overrides.clear()
