"""Legacy identity entities — use domain.organization and domain.membership for new code."""

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
    deleted_at: datetime | None = None
