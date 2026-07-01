from uuid import UUID

from app.modules.identity.api.membership.schemas import (
    AcceptMembershipInviteRequest,
    AcceptMembershipInviteResponse,
    InviteMemberRequest,
    InviteMemberResponse,
    MembershipListResponse,
    MembershipResponse,
)
from app.modules.identity.application.membership.commands import (
    AcceptMembershipInviteCommand,
    InviteMemberCommand,
    ListOrganizationMembershipsCommand,
    RemoveMembershipCommand,
    SuspendMembershipCommand,
)
from app.modules.identity.application.membership.results import (
    AcceptMembershipInviteResult,
    InviteMemberResult,
    MembershipListResult,
    MembershipResult,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


def list_organization_memberships_command(
    organization_id: OrganizationId,
) -> ListOrganizationMembershipsCommand:
    return ListOrganizationMembershipsCommand(organization_id=organization_id)


def invite_member_request_to_command(
    organization_id: OrganizationId,
    invited_by_user_id: UserId,
    payload: InviteMemberRequest,
) -> InviteMemberCommand:
    return InviteMemberCommand(
        organization_id=organization_id,
        invited_by_user_id=invited_by_user_id,
        email=str(payload.email),
    )


def accept_membership_invite_request_to_command(
    payload: AcceptMembershipInviteRequest,
    accepting_user_id: UserId,
) -> AcceptMembershipInviteCommand:
    return AcceptMembershipInviteCommand(
        plain_token=payload.token,
        accepting_user_id=accepting_user_id,
    )


def suspend_membership_command(membership_id: MembershipId) -> SuspendMembershipCommand:
    return SuspendMembershipCommand(membership_id=membership_id)


def remove_membership_command(membership_id: MembershipId) -> RemoveMembershipCommand:
    return RemoveMembershipCommand(membership_id=membership_id)


def membership_result_to_response(result: MembershipResult) -> MembershipResponse:
    return MembershipResponse(
        id=result.membership_id.value,
        user_id=result.user_id.value,
        organization_id=result.organization_id.value,
        status=result.status,
        joined_at=result.joined_at,
    )


def membership_list_result_to_response(result: MembershipListResult) -> MembershipListResponse:
    return MembershipListResponse(
        memberships=[membership_result_to_response(membership) for membership in result.memberships]
    )


def invite_member_result_to_response(result: InviteMemberResult) -> InviteMemberResponse:
    return InviteMemberResponse(
        invite_id=result.invite_id.value,
        token=result.plain_token,
        expires_at=result.expires_at,
    )


def accept_membership_invite_result_to_response(
    result: AcceptMembershipInviteResult,
) -> AcceptMembershipInviteResponse:
    return AcceptMembershipInviteResponse(
        membership=membership_result_to_response(result.membership),
        organization_id=result.organization_id.value,
    )
