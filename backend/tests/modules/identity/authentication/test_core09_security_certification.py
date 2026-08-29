import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.identity.domain.authorization.entities.role import Role
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.infrastructure.authentication.clock import UtcClock
from app.modules.identity.infrastructure.authentication.persistence.models.identity_action_token import (
    IdentityActionTokenModel,
)
from app.modules.identity.infrastructure.authentication.security.identity_action_token_service import (
    IdentityActionTokenService,
)
from app.modules.identity.infrastructure.authorization.persistence.models.user_role import (
    UserRoleModel,
)
from app.modules.identity.infrastructure.authorization.repositories import SqlAlchemyRoleRepository
from app.modules.identity.infrastructure.organization.persistence.models.organization import (
    OrganizationModel,
)
from app.modules.identity.infrastructure.persistence.models import UserModel

_VALID_PASSWORD = "certification password 123"


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


def _app_client(db_session: Session) -> tuple[object, TestClient]:
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


def test_public_signup_cannot_self_assert_super_admin_or_inject_role(
    db_session: Session,
) -> None:
    organization_admin = _seed_organization_admin(db_session)
    app, client = _app_client(db_session)
    try:
        with client:
            response = client.post(
                "/api/v1/auth/signup",
                json={
                    "organization_name": "Adversarial Signup",
                    "organization_slug": "adversarial-signup",
                    "email": "attacker@example.com",
                    "is_super_admin": True,
                    "role": "super_admin",
                    "role_slug": "super_admin",
                },
            )
        assert response.status_code == 202, response.text

        user = db_session.scalar(
            select(UserModel).where(UserModel.email == "attacker@example.com")
        )
        assert user is not None
        assert user.is_super_admin is False
        assert user.status == "inactive"

        assignment = db_session.scalar(
            select(UserRoleModel).where(UserRoleModel.user_id == user.id)
        )
        assert assignment is not None
        assert assignment.role_id == organization_admin.id.value
        assert assignment.organization_id == user.organization_id
    finally:
        app.dependency_overrides.clear()


def test_activation_token_for_org_a_cannot_mutate_org_b(
    db_session: Session,
) -> None:
    _seed_organization_admin(db_session)
    app, client = _app_client(db_session)
    try:
        with client:
            response_a = client.post(
                "/api/v1/auth/signup",
                json={
                    "organization_name": "Certification Org A",
                    "organization_slug": "certification-org-a",
                    "email": "org.a@example.com",
                },
            )
            response_b = client.post(
                "/api/v1/auth/signup",
                json={
                    "organization_name": "Certification Org B",
                    "organization_slug": "certification-org-b",
                    "email": "org.b@example.com",
                },
            )
            assert response_a.status_code == 202, response_a.text
            assert response_b.status_code == 202, response_b.text

            user_a = db_session.scalar(
                select(UserModel).where(UserModel.email == "org.a@example.com")
            )
            user_b = db_session.scalar(
                select(UserModel).where(UserModel.email == "org.b@example.com")
            )
            assert user_a is not None and user_b is not None
            assert user_a.organization_id != user_b.organization_id

            token_a = db_session.scalar(
                select(IdentityActionTokenModel).where(
                    IdentityActionTokenModel.user_id == user_a.id,
                    IdentityActionTokenModel.purpose == "account_activation",
                )
            )
            token_b = db_session.scalar(
                select(IdentityActionTokenModel).where(
                    IdentityActionTokenModel.user_id == user_b.id,
                    IdentityActionTokenModel.purpose == "account_activation",
                )
            )
            assert token_a is not None and token_b is not None

            raw_token_a = IdentityActionTokenService(
                settings.CORE_IDENTITY_ACTION_TOKEN_SECRET_KEY
            ).derive_from_uuid(token_a.id)

            activate_a = client.post(
                "/api/v1/auth/activation/complete",
                json={"token": raw_token_a, "password": _VALID_PASSWORD},
            )
            assert activate_a.status_code == 200, activate_a.text

        db_session.expire_all()
        user_a = db_session.get(UserModel, user_a.id)
        user_b = db_session.get(UserModel, user_b.id)
        org_a = db_session.get(OrganizationModel, user_a.organization_id)
        org_b = db_session.get(OrganizationModel, user_b.organization_id)
        token_b = db_session.get(IdentityActionTokenModel, token_b.id)

        assert user_a is not None and user_a.status == "active"
        assert org_a is not None and org_a.status == "active"
        assert user_b is not None and user_b.status == "inactive"
        assert user_b.password_hash is None
        assert org_b is not None and org_b.status == "pending_activation"
        assert token_b is not None and token_b.consumed_at is None
        assert token_b.invalidated_at is None
    finally:
        app.dependency_overrides.clear()
