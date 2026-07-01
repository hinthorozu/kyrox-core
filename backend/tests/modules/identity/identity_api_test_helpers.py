from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authorization.entities import (
    OrganizationRole,
    Permission,
    PermissionGroup,
    Role,
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


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class IdentityApiSeed:
    user: User
    org: Organization
    permission_code: str


def seed_owner_and_member_roles(db_session: Session) -> SqlAlchemyRoleRepository:
    role_repo = SqlAlchemyRoleRepository(db_session)
    for slug in ("owner", "member"):
        if role_repo.get_by_slug(RoleSlug.create(slug), RoleScope.ORGANIZATION) is None:
            role_repo.add(
                Role(
                    id=RoleId(uuid.uuid4()),
                    name=slug.title(),
                    slug=RoleSlug.create(slug),
                    scope=RoleScope.ORGANIZATION,
                    is_system=True,
                    created_at=_now(),
                    updated_at=_now(),
                )
            )
    db_session.commit()
    return role_repo


def seed_authenticated_user(db_session: Session) -> User:
    seed_owner_and_member_roles(db_session)
    clock = UtcClock()
    user_repo = SqlAlchemyUserRepository(db_session, clock)
    now = clock.now()
    user = user_repo.add(
        User(
            id=UserId(uuid.uuid4()),
            email=Email.create(f"api-{uuid.uuid4().hex[:8]}@example.com"),
            password_hash=Argon2idPasswordHasher().hash("Password123!"),
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()
    return user


def seed_user_with_org_permission(
    db_session: Session,
    *,
    permission_code: str,
) -> IdentityApiSeed:
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
            email=Email.create(f"api-{uuid.uuid4().hex[:8]}@example.com"),
            password_hash=Argon2idPasswordHasher().hash("Password123!"),
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    org = org_repo.add(
        Organization(
            id=OrgEntityId(uuid.uuid4()),
            name=OrganizationName.create("API Test Org"),
            slug=OrganizationSlug.create(f"api-org-{uuid.uuid4().hex[:8]}"),
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
            code=PermissionGroupCode.create("identity.organizations"),
            name="Organizations",
            module=PermissionModule.create("identity"),
            description="Organization permissions",
            sort_order=1,
            is_system=True,
            created_at=now,
            updated_at=now,
        )
    )
    permission = permission_repo.add(
        Permission(
            id=PermissionId(uuid.uuid4()),
            group_id=group.id,
            code=PermissionCode.create(permission_code),
            description="Permission",
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

    return IdentityApiSeed(
        user=user,
        org=org,
        permission_code=permission_code,
    )


def login(client, email: str | Email, password: str = "Password123!") -> str:
    email_value = email.value if isinstance(email, Email) else email
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email_value, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]
