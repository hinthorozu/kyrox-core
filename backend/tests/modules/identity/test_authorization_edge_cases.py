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


class AuthorizationSeed:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session
        self.user_repo = SqlAlchemyUserRepository(db_session)
        self.org_repo = SqlAlchemyOrganizationRepository(db_session)
        self.membership_repo = SqlAlchemyMembershipRepository(db_session)
        self.role_repo = SqlAlchemyRoleRepository(db_session)
        self.permission_repo = SqlAlchemyPermissionRepository(db_session)
        self.role_permission_repo = SqlAlchemyRolePermissionRepository(db_session)
        self.checker = SqlAlchemyPermissionChecker(db_session)

        self.user = self.user_repo.create(
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
        self.org = self.org_repo.create(
            Organization(
                id=uuid.uuid4(),
                name="Acme",
                slug="acme",
                status=OrganizationStatus.ACTIVE,
                created_at=_now(),
                updated_at=_now(),
            )
        )
        self.role = self.role_repo.create(
            Role(
                id=uuid.uuid4(),
                organization_id=self.org.id,
                name="Member",
                slug="member",
                is_system=True,
                created_at=_now(),
                updated_at=_now(),
            )
        )
        self.permission = self.permission_repo.create(
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
        self.role_permission_repo.grant(
            RolePermission(role_id=self.role.id, permission_id=self.permission.id)
        )
        self.membership = self.membership_repo.create(
            Membership(
                id=uuid.uuid4(),
                user_id=self.user.id,
                organization_id=self.org.id,
                status=MembershipStatus.ACTIVE,
                role_id=self.role.id,
                created_at=_now(),
                updated_at=_now(),
            )
        )
        self.db_session.commit()

    def assert_has_permission(self, expected: bool) -> None:
        result = self.checker.has_permission(
            self.user.id,
            self.org.id,
            self.permission.code,
        )
        assert result is expected


def test_checker_rejects_inactive_membership(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    seed.membership.status = MembershipStatus.INACTIVE
    seed.membership.updated_at = _now()
    seed.membership_repo.update(seed.membership)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_suspended_membership(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    seed.membership.status = MembershipStatus.SUSPENDED
    seed.membership.updated_at = _now()
    seed.membership_repo.update(seed.membership)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_deleted_membership(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    seed.membership_repo.soft_delete(seed.membership.id)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_null_role_id(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    seed.membership.role_id = None
    seed.membership.updated_at = _now()
    seed.membership_repo.update(seed.membership)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_soft_deleted_role(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    seed.role_repo.soft_delete(seed.role.id)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_wrong_organization_role(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    other_org = seed.org_repo.create(
        Organization(
            id=uuid.uuid4(),
            name="Other",
            slug="other",
            status=OrganizationStatus.ACTIVE,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    foreign_role = seed.role_repo.create(
        Role(
            id=uuid.uuid4(),
            organization_id=other_org.id,
            name="Foreign",
            slug="foreign",
            is_system=True,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    seed.membership.role_id = foreign_role.id
    seed.membership.updated_at = _now()
    seed.membership_repo.update(seed.membership)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_inactive_organization(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    org = seed.org_repo.get_by_id(seed.org.id)
    assert org is not None
    org.status = OrganizationStatus.SUSPENDED
    org.updated_at = _now()
    seed.org_repo.update(org)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_deleted_organization(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    seed.org_repo.soft_delete(seed.org.id)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_service_super_admin_bypasses_core_permission(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    user = seed.user_repo.get_by_id(seed.user.id)
    assert user is not None
    user.is_super_admin = True
    user.updated_at = _now()
    seed.user_repo.update(user)
    seed.membership_repo.soft_delete(seed.membership.id)
    seed.db_session.commit()

    service = AuthorizationService(
        permission_checker=seed.checker,
        user_repository=seed.user_repo,
    )

    assert service.has_permission(seed.user.id, seed.org.id, "core.user.read") is True


def test_service_super_admin_does_not_bypass_non_core_permission(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    user = seed.user_repo.get_by_id(seed.user.id)
    assert user is not None
    user.is_super_admin = True
    user.updated_at = _now()
    seed.user_repo.update(user)
    seed.db_session.commit()

    service = AuthorizationService(
        permission_checker=seed.checker,
        user_repository=seed.user_repo,
    )

    assert service.has_permission(seed.user.id, seed.org.id, "product.user.read") is False


def test_service_super_admin_requires_active_user(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    user = seed.user_repo.get_by_id(seed.user.id)
    assert user is not None
    user.is_super_admin = True
    user.status = UserStatus.SUSPENDED
    user.updated_at = _now()
    seed.user_repo.update(user)
    seed.db_session.commit()

    service = AuthorizationService(
        permission_checker=seed.checker,
        user_repository=seed.user_repo,
    )

    assert service.has_permission(seed.user.id, seed.org.id, "core.user.read") is False
