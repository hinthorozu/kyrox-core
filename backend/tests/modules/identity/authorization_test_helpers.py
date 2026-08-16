import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.identity.application.authorization import AuthorizationService
from app.modules.identity.domain.authorization.entities import (
    Permission,
    PermissionGroup,
    Role,
    RolePermission,
    UserRole,
)
from app.modules.identity.domain.authorization.enums import AssignmentStatus, RoleScope
from app.modules.identity.domain.authorization.value_objects.identity import (
    OrganizationId,
    PermissionGroupId,
    PermissionId,
    RoleId,
    UserId,
    UserRoleId,
)
from app.modules.identity.domain.authorization.value_objects.rbac import (
    PermissionCode,
    PermissionGroupCode,
    PermissionModule,
    RoleSlug,
)
from app.modules.identity.domain.entities import Organization, User
from app.modules.identity.domain.enums import OrganizationStatus, UserStatus
from app.modules.identity.infrastructure.authorization.persistence.models.permission_group import (
    PermissionGroupModel,
)
from app.modules.identity.infrastructure.authorization.repositories import (
    SqlAlchemyPermissionGroupRepository,
    SqlAlchemyPermissionRepository,
    SqlAlchemyRolePermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRoleRepository,
)
from app.modules.identity.infrastructure.authorization.services import (
    SqlAlchemyPermissionChecker,
    SqlAlchemyPlatformUserReader,
)
from app.modules.identity.infrastructure.persistence.models import UserModel
from app.modules.identity.infrastructure.repositories import (
    SqlAlchemyOrganizationRepository,
    SqlAlchemyUserRepository,
)


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def seed_core_permission_group(db_session: Session) -> PermissionGroupId:
    group_id = PermissionGroupId(uuid.uuid4())
    now = _now()
    db_session.add(
        PermissionGroupModel(
            id=group_id.value,
            code="core",
            name="Core",
            module="core",
            description="Core permissions",
            sort_order=1,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()
    return group_id


def build_authorization_service(db_session: Session) -> AuthorizationService:
    return AuthorizationService(
        platform_user_reader=SqlAlchemyPlatformUserReader(db_session),
        permission_checker=SqlAlchemyPermissionChecker(db_session),
    )


@dataclass
class UserRolePermissionSeed:
    user: User
    org: Organization
    permission_code: str
    role: Role
    permission: Permission
    user_role: UserRole
    user_repo: SqlAlchemyUserRepository
    org_repo: SqlAlchemyOrganizationRepository
    role_repo: SqlAlchemyRoleRepository
    permission_repo: SqlAlchemyPermissionRepository
    role_permission_repo: SqlAlchemyRolePermissionRepository
    user_role_repo: SqlAlchemyUserRoleRepository
    checker: SqlAlchemyPermissionChecker
    db_session: Session


def seed_user_role_with_permission(
    db_session: Session,
    *,
    permission_code: str = "core.user.read",
) -> UserRolePermissionSeed:
    seed_core_permission_group(db_session)
    user_repo = SqlAlchemyUserRepository(db_session)
    org_repo = SqlAlchemyOrganizationRepository(db_session)
    role_repo = SqlAlchemyRoleRepository(db_session)
    group_repo = SqlAlchemyPermissionGroupRepository(db_session)
    permission_repo = SqlAlchemyPermissionRepository(db_session)
    role_permission_repo = SqlAlchemyRolePermissionRepository(db_session)
    user_role_repo = SqlAlchemyUserRoleRepository(db_session)
    checker = SqlAlchemyPermissionChecker(db_session)

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
    user_model = db_session.get(UserModel, user.id)
    assert user_model is not None
    user_model.organization_id = org.id
    db_session.flush()

    role = role_repo.add(
        Role(
            id=RoleId(uuid.uuid4()),
            name="Member",
            slug=RoleSlug.create("member"),
            scope=RoleScope.ORGANIZATION,
            is_system=True,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    group = group_repo.add(
        PermissionGroup(
            id=PermissionGroupId(uuid.uuid4()),
            code=PermissionGroupCode.create("core.users"),
            name="Users",
            module=PermissionModule.create("core"),
            description="Core user permissions",
            sort_order=1,
            is_system=True,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    permission = permission_repo.add(
        Permission(
            id=PermissionId(uuid.uuid4()),
            group_id=group.id,
            code=PermissionCode.create(permission_code),
            description="Permission",
            is_system=True,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    role_permission_repo.grant(RolePermission(role_id=role.id, permission_id=permission.id))
    user_role = user_role_repo.add(
        UserRole(
            id=UserRoleId(uuid.uuid4()),
            user_id=UserId(user.id),
            organization_id=OrganizationId(org.id),
            role_id=role.id,
            status=AssignmentStatus.ACTIVE,
            assigned_at=_now(),
        )
    )
    db_session.commit()

    return UserRolePermissionSeed(
        user=user,
        org=org,
        permission_code=permission_code,
        role=role,
        permission=permission,
        user_role=user_role,
        user_repo=user_repo,
        org_repo=org_repo,
        role_repo=role_repo,
        permission_repo=permission_repo,
        role_permission_repo=role_permission_repo,
        user_role_repo=user_role_repo,
        checker=checker,
        db_session=db_session,
    )
