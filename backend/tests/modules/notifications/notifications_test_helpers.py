import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "identity"))
from identity_api_test_helpers import seed_owner_and_member_roles

from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authorization.entities import (
    OrganizationRole,
    Permission,
    PermissionGroup,
    RolePermission,
    UserRole,
)
from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity import (
    OrganizationId,
    OrganizationRoleId,
    PermissionGroupId,
    PermissionId,
    RoleId,
    UserRoleId,
)
from app.modules.identity.domain.authorization.value_objects.rbac import (
    PermissionCode,
    PermissionGroupCode,
    PermissionModule,
    RoleSlug,
)
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId as OrgEntityId,
)
from app.modules.identity.domain.organization.value_objects.profile.organization_name import OrganizationName
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import OrganizationSlug
from app.modules.identity.infrastructure.authentication.clock import UtcClock
from app.modules.identity.infrastructure.authentication.repositories import SqlAlchemyUserRepository
from app.modules.identity.infrastructure.authentication.security import Argon2idPasswordHasher
from app.modules.identity.infrastructure.authorization.repositories import (
    SqlAlchemyOrganizationRoleRepository,
    SqlAlchemyPermissionGroupRepository,
    SqlAlchemyPermissionRepository,
    SqlAlchemyRolePermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRoleRepository,
)
from app.modules.identity.infrastructure.organization.repositories import SqlAlchemyOrganizationRepository


def seed_user_with_notification_permissions(
    db_session: Session,
    *,
    permission_codes: tuple[str, ...] = (
        "notifications.platform.send",
        "notifications.platform.read",
    ),
):
    user_repo = SqlAlchemyUserRepository(db_session, UtcClock())
    org_repo = SqlAlchemyOrganizationRepository(db_session, UtcClock())
    role_repo = seed_owner_and_member_roles(db_session)
    group_repo = SqlAlchemyPermissionGroupRepository(db_session)
    permission_repo = SqlAlchemyPermissionRepository(db_session)
    role_permission_repo = SqlAlchemyRolePermissionRepository(db_session)
    org_role_repo = SqlAlchemyOrganizationRoleRepository(db_session)
    user_role_repo = SqlAlchemyUserRoleRepository(db_session)

    clock = UtcClock()
    now = clock.now()
    user = user_repo.add(
        User(
            id=UserId(uuid.uuid4()),
            email=Email.create(f"notifications-api-{uuid.uuid4().hex[:8]}@example.com"),
            password_hash=Argon2idPasswordHasher().hash("Password123!"),
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    org = org_repo.add(
        Organization(
            id=OrgEntityId(uuid.uuid4()),
            name=OrganizationName.create("Notifications API Org"),
            slug=OrganizationSlug.create(f"notifications-org-{uuid.uuid4().hex[:8]}"),
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    role = role_repo.get_by_slug(RoleSlug.create("member"), RoleScope.ORGANIZATION)
    assert role is not None
    group = group_repo.add(
        PermissionGroup(
            id=PermissionGroupId(uuid.uuid4()),
            code=PermissionGroupCode.create("notifications.platform"),
            name="Platform Notifications",
            module=PermissionModule.create("notifications"),
            description="Notifications permissions",
            sort_order=1,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
    )
    for permission_code in permission_codes:
        permission = permission_repo.add(
            Permission(
                id=PermissionId(uuid.uuid4()),
                group_id=group.id,
                code=PermissionCode.create(permission_code),
                description="Notifications permission",
                is_system=True,
                created_at=now,
                updated_at=now,
            )
        )
        role_permission_repo.grant(RolePermission(role_id=role.id, permission_id=permission.id))
    org_role = org_role_repo.add(
        OrganizationRole(
            id=OrganizationRoleId(uuid.uuid4()),
            organization_id=OrganizationId(org.id.value),
            role_id=role.id,
            status=AssignmentStatus.ACTIVE,
            is_default=True,
            created_at=now,
            updated_at=now,
        )
    )
    user_role_repo.add(
        UserRole(
            id=UserRoleId(uuid.uuid4()),
            user_id=UserId(user.id.value),
            organization_id=OrganizationId(org.id.value),
            organization_role_id=org_role.id,
            status=AssignmentStatus.ACTIVE,
            assigned_at=now,
        )
    )
    db_session.commit()
    return user, org
