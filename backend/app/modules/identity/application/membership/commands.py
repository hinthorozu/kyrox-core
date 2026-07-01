from dataclasses import dataclass

from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


@dataclass(frozen=True, slots=True)
class ListOrganizationMembershipsCommand:
    organization_id: OrganizationId


@dataclass(frozen=True, slots=True)
class InviteMemberCommand:
    organization_id: OrganizationId
    invited_by_user_id: UserId
    email: str


@dataclass(frozen=True, slots=True)
class AcceptMembershipInviteCommand:
    plain_token: str
    accepting_user_id: UserId


@dataclass(frozen=True, slots=True)
class SuspendMembershipCommand:
    membership_id: MembershipId


@dataclass(frozen=True, slots=True)
class RemoveMembershipCommand:
    membership_id: MembershipId
