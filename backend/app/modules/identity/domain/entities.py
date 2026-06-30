from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.identity.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
)


@dataclass
class User:
    id: UUID
    email: str
    password_hash: str | None
    status: UserStatus
    is_super_admin: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


@dataclass
class Organization:
    id: UUID
    name: str
    slug: str
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


@dataclass
class Membership:
    id: UUID
    user_id: UUID
    organization_id: UUID
    status: MembershipStatus
    created_at: datetime
    updated_at: datetime
    role_id: UUID | None = None
    deleted_at: datetime | None = None


@dataclass
class Role:
    id: UUID
    organization_id: UUID | None
    name: str
    slug: str
    is_system: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


@dataclass
class Permission:
    id: UUID
    code: str
    description: str
    module: str
    is_system: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RolePermission:
    role_id: UUID
    permission_id: UUID


@dataclass
class Session:
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None


@dataclass
class RefreshToken:
    id: UUID
    session_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None
