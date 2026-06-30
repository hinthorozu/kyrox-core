import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import get_db
from app.modules.identity.api.context import AuthorizationContext
from app.modules.identity.api.dependencies import get_authorization_service
from app.modules.identity.api.guards import get_authorization_context, require_permission
from app.modules.identity.application.authorization import AuthorizationService
from app.modules.identity.domain.entities import (
    Membership,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
)
from app.modules.identity.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
)
from app.modules.identity.domain.ports import AccessTokenClaims
from app.modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401
from app.modules.identity.infrastructure.repositories import (
    SqlAlchemyMembershipRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyPermissionChecker,
    SqlAlchemyPermissionRepository,
    SqlAlchemyRolePermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)


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


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def _seed(db_session: Session) -> tuple[User, Organization, AccessTokenClaims]:
    user_repo = SqlAlchemyUserRepository(db_session)
    org_repo = SqlAlchemyOrganizationRepository(db_session)
    membership_repo = SqlAlchemyMembershipRepository(db_session)
    role_repo = SqlAlchemyRoleRepository(db_session)
    permission_repo = SqlAlchemyPermissionRepository(db_session)
    role_permission_repo = SqlAlchemyRolePermissionRepository(db_session)

    user = user_repo.create(
        User(
            id=uuid.uuid4(),
            email="guard@example.com",
            password_hash="hash",
            status=UserStatus.ACTIVE,
            is_super_admin=False,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    org = org_repo.create(
        Organization(
            id=uuid.uuid4(),
            name="Acme",
            slug="acme",
            status=OrganizationStatus.ACTIVE,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    role = role_repo.create(
        Role(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="Member",
            slug="member",
            is_system=True,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    permission = permission_repo.create(
        Permission(
            id=uuid.uuid4(),
            code="core.user.read",
            description="Read users",
            module="core",
            is_system=True,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    role_permission_repo.grant(RolePermission(role_id=role.id, permission_id=permission.id))
    membership_repo.create(
        Membership(
            id=uuid.uuid4(),
            user_id=user.id,
            organization_id=org.id,
            status=MembershipStatus.ACTIVE,
            role_id=role.id,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    db_session.commit()

    now = _now()
    claims = AccessTokenClaims(
        sub=user.id,
        email=user.email,
        sid=uuid.uuid4(),
        exp=now + timedelta(minutes=15),
        iat=now,
        jti=uuid.uuid4(),
    )
    return user, org, claims


@pytest.fixture
def guard_client(db_session: Session) -> Generator[TestClient, None, None]:
    router = APIRouter()

    @router.get("/protected")
    def protected_route(
        context: AuthorizationContext = Depends(require_permission("core.user.read")),
    ) -> dict[str, str]:
        return {
            "user_id": str(context.user_id),
            "organization_id": str(context.organization_id),
        }

    @router.get("/denied")
    def denied_route(
        context: AuthorizationContext = Depends(require_permission("core.user.create")),
    ) -> dict[str, str]:
        return {"user_id": str(context.user_id)}

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    def override_auth_service() -> AuthorizationService:
        return AuthorizationService(
            permission_checker=SqlAlchemyPermissionChecker(db_session),
            user_repository=SqlAlchemyUserRepository(db_session),
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_authorization_service] = override_auth_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_require_permission_guard_allows_authorized_request(
    guard_client: TestClient,
    db_session: Session,
) -> None:
    user, org, claims = _seed(db_session)

    def override_context() -> AuthorizationContext:
        return AuthorizationContext(
            user_id=claims.sub,
            organization_id=org.id,
            email=claims.email,
        )

    guard_client.app.dependency_overrides[get_authorization_context] = override_context

    response = guard_client.get("/protected")

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.id)


def test_require_permission_guard_rejects_missing_permission(
    guard_client: TestClient,
    db_session: Session,
) -> None:
    user, org, claims = _seed(db_session)

    def override_context() -> AuthorizationContext:
        return AuthorizationContext(
            user_id=claims.sub,
            organization_id=org.id,
            email=claims.email,
        )

    guard_client.app.dependency_overrides[get_authorization_context] = override_context

    response = guard_client.get("/denied")

    assert response.status_code == 403
