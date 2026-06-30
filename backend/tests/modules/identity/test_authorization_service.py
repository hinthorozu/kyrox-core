import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
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
from app.modules.identity.domain.exceptions import PermissionDeniedError
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
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def _build_authorization_service(db_session: Session) -> AuthorizationService:
    return AuthorizationService(
        permission_checker=SqlAlchemyPermissionChecker(db_session),
        user_repository=SqlAlchemyUserRepository(db_session),
    )


def _seed_member_with_permission(db_session: Session) -> tuple[User, Organization, str]:
    user_repo = SqlAlchemyUserRepository(db_session)
    org_repo = SqlAlchemyOrganizationRepository(db_session)
    membership_repo = SqlAlchemyMembershipRepository(db_session)
    role_repo = SqlAlchemyRoleRepository(db_session)
    permission_repo = SqlAlchemyPermissionRepository(db_session)
    role_permission_repo = SqlAlchemyRolePermissionRepository(db_session)

    user = user_repo.create(
        User(
            id=uuid.uuid4(),
            email="member@example.com",
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
    return user, org, permission.code


def test_authorization_service_has_permission(db_session: Session) -> None:
    user, org, permission_code = _seed_member_with_permission(db_session)
    service = _build_authorization_service(db_session)

    assert service.has_permission(user.id, org.id, permission_code) is True
    assert service.has_permission(user.id, org.id, "core.user.create") is False


def test_authorization_service_require_permission(db_session: Session) -> None:
    user, org, permission_code = _seed_member_with_permission(db_session)
    service = _build_authorization_service(db_session)

    service.require_permission(user.id, org.id, permission_code)

    with pytest.raises(PermissionDeniedError):
        service.require_permission(user.id, org.id, "core.user.create")


def test_authorization_service_rejects_inactive_user(db_session: Session) -> None:
    user, org, permission_code = _seed_member_with_permission(db_session)
    user_repo = SqlAlchemyUserRepository(db_session)
    inactive_user = user_repo.get_by_id(user.id)
    assert inactive_user is not None
    inactive_user.status = UserStatus.SUSPENDED
    inactive_user.updated_at = _now()
    user_repo.update(inactive_user)
    db_session.commit()

    service = _build_authorization_service(db_session)
    assert service.has_permission(user.id, org.id, permission_code) is False
