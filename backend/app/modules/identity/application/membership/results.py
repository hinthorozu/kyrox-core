from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.value_objects.identity.invite_id import InviteId
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId


@dataclass(frozen=True, slots=True)
class MembershipResult:
    membership_id: MembershipId
    user_id: UserId
    organization_id: OrganizationId
    status: MembershipStatus
    joined_at: datetime | None


@dataclass(frozen=True, slots=True)
class MembershipListResult:
    memberships: list[MembershipResult]


@dataclass(frozen=True, slots=True)
class InviteMemberResult:
    invite_id: InviteId
    plain_token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AcceptMembershipInviteResult:
    membership: MembershipResult
    organization_id: OrganizationId
