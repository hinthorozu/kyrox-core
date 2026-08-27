import json
import uuid
from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.identity.application.authentication.id_generator import Uuid4IdGenerator
from app.modules.identity.application.authentication.identity_action_tokens import (
    IssueIdentityActionToken,
    MaterializeIdentityActionToken,
)
from app.modules.identity.application.authentication.public_signup import (
    ActivationNotificationPort,
    PublicSignupCommand,
    PublicSignupUseCase,
)
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.exceptions.authentication import (
    PublicSignupConflictError,
    PublicSignupProvisioningError,
)
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.entities.role import Role
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.infrastructure.authentication.clock import UtcClock
from app.modules.identity.infrastructure.authentication.persistence.models.identity_action_token import (
    IdentityActionTokenModel,
)
from app.modules.identity.infrastructure.authentication.repositories import (
    SqlAlchemyIdentityActionTokenRepository,
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.authentication.security.identity_action_token_service import (
    IdentityActionTokenService,
)
from app.modules.identity.infrastructure.authorization.persistence.models.user_role import (
    UserRoleModel,
)
from app.modules.identity.infrastructure.authorization.repositories import (
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRoleRepository,
)
from app.modules.identity.infrastructure.organization.persistence.models.organization import (
    OrganizationModel,
)
from app.modules.identity.infrastructure.organization.repositories import (
    SqlAlchemyOrganizationRepository,
)
from app.modules.identity.infrastructure.persistence.models import UserModel
from app.modules.jobs.infrastructure.persistence.models import PlatformJobModel
from app.modules.notifications.infrastructure.persistence.models import PlatformNotificationModel


class SuccessfulActivationNotificationPort(ActivationNotificationPort):
    def __init__(self) -> None:
        self.notification_id = uuid.uuid4()
        self.calls: list[tuple[str, UserId, IdentityActionTokenId]] = []

    def enqueue_activation(
        self,
        *,
        recipient: str,
        user_id: UserId,
        token_id: IdentityActionTokenId,
    ) -> uuid.UUID:
        self.calls.append((recipient, user_id, token_id))
        return self.notification_id


class FailingActivationNotificationPort(ActivationNotificationPort):
    def enqueue_activation(
        self,
        *,
        recipient: str,
        user_id: UserId,
        token_id: IdentityActionTokenId,
    ) -> uuid.UUID:
        raise PublicSignupProvisioningError("forced notification failure")


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


def _seed_organization_admin(db_session: Session) -> Role:
    clock = UtcClock()
    now = clock.now()
    repository = SqlAlchemyRoleRepository(db_session)
    existing = repository.get_by_slug(
        RoleSlug.create("organization_admin"),
        RoleScope.ORGANIZATION,
    )
    if existing is not None:
        return existing
    role = repository.add(
        Role(
            id=RoleId(uuid.uuid4()),
            name="OrganizationAdmin",
            slug=RoleSlug.create("organization_admin"),
            scope=RoleScope.ORGANIZATION,
            is_system=True,
            created_at=now,
            updated_at=now,
            is_assignable=True,
            is_protected=True,
        )
    )
    db_session.commit()
    return role


def _build_use_case(
    db_session: Session,
    notification_port: ActivationNotificationPort,
) -> PublicSignupUseCase:
    clock = UtcClock()
    id_generator = Uuid4IdGenerator()
    token_repository = SqlAlchemyIdentityActionTokenRepository(db_session)
    token_service = IdentityActionTokenService("t" * 48)
    issue = IssueIdentityActionToken(
        repository=token_repository,
        token_service=token_service,
        clock=clock,
        id_generator=id_generator,
    )
    return PublicSignupUseCase(
        organization_repository=SqlAlchemyOrganizationRepository(db_session, clock),
        user_repository=SqlAlchemyUserRepository(db_session, clock),
        role_repository=SqlAlchemyRoleRepository(db_session),
        user_role_repository=SqlAlchemyUserRoleRepository(db_session),
        issue_identity_action_token=issue,
        activation_notification_port=notification_port,
        clock=clock,
        id_generator=id_generator,
        activation_token_ttl=timedelta(hours=24),
    )


def test_public_signup_creates_pending_bootstrap_without_password_or_super_admin(
    db_session: Session,
) -> None:
    role = _seed_organization_admin(db_session)
    notification_port = SuccessfulActivationNotificationPort()
    use_case = _build_use_case(db_session, notification_port)

    result = use_case.execute(
        PublicSignupCommand(
            organization_name="Acme Turkey",
            organization_slug="acme-turkey",
            email="First.Admin@Example.com",
        )
    )

    organization = db_session.get(OrganizationModel, result.organization_id)
    user = db_session.get(UserModel, result.user_id)
    assignment = db_session.scalar(
        select(UserRoleModel).where(UserRoleModel.user_id == result.user_id)
    )
    token = db_session.scalar(
        select(IdentityActionTokenModel).where(
            IdentityActionTokenModel.user_id == result.user_id
        )
    )

    assert organization is not None
    assert organization.status == "pending_activation"
    assert user is not None
    assert user.email == "first.admin@example.com"
    assert user.status == "inactive"
    assert user.password_hash is None
    assert user.is_super_admin is False
    assert user.organization_id == organization.id
    assert assignment is not None
    assert assignment.organization_id == organization.id
    assert assignment.role_id == role.id.value
    assert assignment.assigned_by is None
    assert token is not None
    assert token.purpose == "account_activation"
    assert notification_port.calls
    assert notification_port.calls[0][0] == user.email


def test_public_signup_reconstructable_token_is_hash_only_and_materializable(
    db_session: Session,
) -> None:
    _seed_organization_admin(db_session)
    notification_port = SuccessfulActivationNotificationPort()
    use_case = _build_use_case(db_session, notification_port)

    result = use_case.execute(
        PublicSignupCommand(
            organization_name="Secure Bootstrap",
            email="secure@example.com",
        )
    )
    token = db_session.scalar(
        select(IdentityActionTokenModel).where(
            IdentityActionTokenModel.user_id == result.user_id
        )
    )
    assert token is not None

    service = IdentityActionTokenService("t" * 48)
    raw_token = service.derive(IdentityActionTokenId(token.id))
    assert token.token_hash == service.hash(raw_token).value
    assert raw_token != token.token_hash
    assert not hasattr(token, "raw_token")

    materializer = MaterializeIdentityActionToken(
        repository=SqlAlchemyIdentityActionTokenRepository(db_session),
        token_service=service,
        clock=UtcClock(),
    )
    assert materializer.execute(
        IdentityActionTokenId(token.id),
        IdentityActionTokenPurpose.ACCOUNT_ACTIVATION,
    ) == raw_token


def test_public_signup_duplicate_email_and_slug_are_safe_conflicts(
    db_session: Session,
) -> None:
    _seed_organization_admin(db_session)
    use_case = _build_use_case(db_session, SuccessfulActivationNotificationPort())
    use_case.execute(
        PublicSignupCommand(
            organization_name="Existing",
            organization_slug="existing-org",
            email="existing@example.com",
        )
    )

    with pytest.raises(PublicSignupConflictError):
        use_case.execute(
            PublicSignupCommand(
                organization_name="Other",
                organization_slug="other-org",
                email="existing@example.com",
            )
        )

    with pytest.raises(PublicSignupConflictError):
        use_case.execute(
            PublicSignupCommand(
                organization_name="Other",
                organization_slug="existing-org",
                email="other@example.com",
            )
        )


def test_public_signup_failure_rolls_back_all_bootstrap_writes(
    db_session: Session,
) -> None:
    _seed_organization_admin(db_session)
    use_case = _build_use_case(db_session, FailingActivationNotificationPort())

    with pytest.raises(PublicSignupProvisioningError):
        use_case.execute(
            PublicSignupCommand(
                organization_name="Rollback Org",
                organization_slug="rollback-org",
                email="rollback@example.com",
            )
        )
    db_session.rollback()

    assert db_session.scalar(select(func.count()).select_from(OrganizationModel)) == 0
    assert db_session.scalar(
        select(func.count()).select_from(UserModel).where(
            UserModel.email == "rollback@example.com"
        )
    ) == 0
    assert db_session.scalar(select(func.count()).select_from(UserRoleModel)) == 0
    assert db_session.scalar(
        select(func.count()).select_from(IdentityActionTokenModel)
    ) == 0


def test_public_signup_api_persists_no_raw_activation_token(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _seed_organization_admin(db_session)
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/signup",
                json={
                    "organization_name": "API Signup",
                    "organization_slug": "api-signup",
                    "email": "api.signup@example.com",
                },
            )
            assert response.status_code == 202, response.text

            user = db_session.scalar(
                select(UserModel).where(UserModel.email == "api.signup@example.com")
            )
            assert user is not None
            token = db_session.scalar(
                select(IdentityActionTokenModel).where(
                    IdentityActionTokenModel.user_id == user.id
                )
            )
            notification = db_session.scalar(
                select(PlatformNotificationModel).where(
                    PlatformNotificationModel.recipient == user.email
                )
            )
            assert token is not None
            assert notification is not None
            job = db_session.scalar(
                select(PlatformJobModel).where(
                    PlatformJobModel.id == notification.job_id
                )
            )
            assert job is not None

            service = IdentityActionTokenService(
                settings.CORE_IDENTITY_ACTION_TOKEN_SECRET_KEY
            )
            raw_token = service.derive(IdentityActionTokenId(token.id))
            persisted_notification = notification.body + json.dumps(
                notification.variables,
                sort_keys=True,
            )
            persisted_job = json.dumps(job.payload, sort_keys=True)

            assert raw_token not in persisted_notification
            assert raw_token not in persisted_job
            assert raw_token not in response.text
            assert raw_token not in caplog.text
            assert notification.variables == {
                "identity_action_token_id": str(token.id)
            }

            login_response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "api.signup@example.com",
                    "password": "not-yet-set",
                },
            )
            assert login_response.status_code == 403
    finally:
        app.dependency_overrides.clear()
