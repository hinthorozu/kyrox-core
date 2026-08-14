import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.modules.identity.application.authorization import CheckPermissionCommand
from app.modules.identity.domain.authorization.entities import Role, RolePermission
from app.modules.identity.domain.authorization.enums import AssignmentStatus, RoleScope
from app.modules.identity.domain.authorization.value_objects.identity import (
    OrganizationId,
    RoleId,
    UserId,
)
from app.modules.identity.domain.authorization.value_objects.rbac import RoleSlug
from app.modules.identity.domain.entities import Organization
from app.modules.identity.domain.enums import OrganizationStatus, UserStatus
from app.modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401
from app.modules.identity.infrastructure.authorization.persistence.models import RoleModel
from authorization_test_helpers import build_authorization_service, seed_user_role_with_permission


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
        self.seed = seed_user_role_with_permission(db_session)

    @property
    def db_session(self) -> Session:
        return self.seed.db_session

    @property
    def user(self):
        return self.seed.user

    @property
    def org(self):
        return self.seed.org

    @property
    def user_repo(self):
        return self.seed.user_repo

    @property
    def org_repo(self):
        return self.seed.org_repo

    @property
    def role_repo(self):
        return self.seed.role_repo

    @property
    def user_role_repo(self):
        return self.seed.user_role_repo

    @property
    def user_role(self):
        return self.seed.user_role

    @property
    def role(self):
        return self.seed.role

    @property
    def permission(self):
        return self.seed.permission

    @property
    def checker(self):
        return self.seed.checker

    def assert_has_permission(self, expected: bool) -> None:
        result = self.checker.has_permission(
            UserId(self.user.id),
            OrganizationId(self.org.id),
            self.permission.code,
        )
        assert result is expected


def test_checker_rejects_inactive_user_role(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    user_role = seed.user_role_repo.get_by_id(seed.user_role.id)
    assert user_role is not None
    user_role.status = AssignmentStatus.INACTIVE
    seed.user_role_repo.update(user_role)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_revoked_user_role(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    seed.user_role_repo.revoke(seed.user_role.id)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_removed_user_role(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    seed.user_role_repo.remove(seed.user_role.id)
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_inactive_organization_role(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    role = seed.db_session.get(RoleModel, seed.role.id.value)
    assert role is not None
    role.is_assignable = False
    seed.db_session.commit()

    seed.assert_has_permission(False)


def test_checker_rejects_soft_deleted_role(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    seed.role_repo.remove(seed.role.id)
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
    foreign_role = seed.role_repo.add(
        Role(
            id=RoleId(uuid.uuid4()),
            name="Foreign",
            slug=RoleSlug.create("foreign"),
            scope=RoleScope.ORGANIZATION,
            is_system=True,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    foreign_role_model = seed.db_session.get(RoleModel, foreign_role.id.value)
    assert foreign_role_model is not None
    foreign_role_model.organization_id = other_org.id
    seed.seed.role_permission_repo.grant(
        RolePermission(role_id=foreign_role.id, permission_id=seed.permission.id)
    )
    user_role = seed.user_role_repo.get_by_id(seed.user_role.id)
    assert user_role is not None
    user_role.role_id = foreign_role.id
    seed.user_role_repo.update(user_role)
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
    seed.user_role_repo.revoke(seed.user_role.id)
    seed.db_session.commit()

    service = build_authorization_service(db_session)

    assert service.has_permission(
        CheckPermissionCommand(
            user_id=UserId(seed.user.id),
            organization_id=OrganizationId(seed.org.id),
            permission_code="core.user.read",
        )
    )


def test_service_super_admin_bypasses_non_core_permission(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    user = seed.user_repo.get_by_id(seed.user.id)
    assert user is not None
    user.is_super_admin = True
    user.updated_at = _now()
    seed.user_repo.update(user)
    seed.db_session.commit()

    service = build_authorization_service(db_session)

    assert (
        service.has_permission(
            CheckPermissionCommand(
                user_id=UserId(seed.user.id),
                organization_id=OrganizationId(seed.org.id),
                permission_code="product.user.read",
            )
        )
        is True
    )


def test_service_super_admin_bypasses_account_status(db_session: Session) -> None:
    seed = AuthorizationSeed(db_session)
    user = seed.user_repo.get_by_id(seed.user.id)
    assert user is not None
    user.is_super_admin = True
    user.status = UserStatus.SUSPENDED
    user.updated_at = _now()
    seed.user_repo.update(user)
    seed.db_session.commit()

    service = build_authorization_service(db_session)

    assert (
        service.has_permission(
            CheckPermissionCommand(
                user_id=UserId(seed.user.id),
                organization_id=OrganizationId(seed.org.id),
                permission_code="core.user.read",
            )
        )
        is True
    )
