from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.authorization.guards import get_access_token_claims, require_permission
from app.modules.identity.api.membership.dependencies import (
    assert_organization_scope,
    get_accept_membership_invite_use_case,
    get_invite_member_use_case,
    get_list_organization_memberships_use_case,
    get_remove_membership_use_case,
    get_suspend_membership_use_case,
    require_scoped_membership,
)
from app.modules.identity.api.membership.error_mapping import map_membership_error, map_membership_flow_error
from app.modules.identity.api.membership.mappers import (
    accept_membership_invite_request_to_command,
    accept_membership_invite_result_to_response,
    invite_member_request_to_command,
    invite_member_result_to_response,
    list_organization_memberships_command,
    membership_list_result_to_response,
    membership_result_to_response,
    remove_membership_command,
    suspend_membership_command,
)
from app.modules.identity.api.membership.schemas import (
    AcceptMembershipInviteRequest,
    AcceptMembershipInviteResponse,
    ErrorResponse,
    InviteMemberRequest,
    InviteMemberResponse,
    MembershipListResponse,
    MembershipResponse,
)
from app.modules.identity.application.membership.accept_membership_invite import AcceptMembershipInviteUseCase
from app.modules.identity.application.membership.invite_member import InviteMemberUseCase
from app.modules.identity.application.membership.list_organization_memberships import (
    ListOrganizationMembershipsUseCase,
)
from app.modules.identity.application.membership.suspend_membership import (
    RemoveMembershipUseCase,
    SuspendMembershipUseCase,
)
from app.modules.identity.domain.authentication.exceptions import InactiveUserError
from app.modules.identity.domain.authentication.value_objects.security.access_token import AccessTokenClaims
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.exceptions import MembershipError
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.exceptions import OrganizationError
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId

router = APIRouter(tags=["memberships"])


@router.get(
    "/organizations/{organization_id}/memberships",
    response_model=MembershipListResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def list_organization_memberships(
    organization_id: UUID,
    context: AuthorizationContext = Depends(require_permission("identity.memberships.read")),
    use_case: ListOrganizationMembershipsUseCase = Depends(get_list_organization_memberships_use_case),
) -> MembershipListResponse:
    assert_organization_scope(organization_id, context)
    try:
        result = use_case.execute(list_organization_memberships_command(OrganizationId(organization_id)))
    except OrganizationError as exc:
        raise map_membership_flow_error(exc) from exc

    return membership_list_result_to_response(result)


@router.post(
    "/organizations/{organization_id}/memberships/invite",
    response_model=InviteMemberResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        410: {"model": ErrorResponse},
    },
)
def invite_member(
    organization_id: UUID,
    payload: InviteMemberRequest,
    context: AuthorizationContext = Depends(require_permission("identity.memberships.invite")),
    use_case: InviteMemberUseCase = Depends(get_invite_member_use_case),
) -> InviteMemberResponse:
    assert_organization_scope(organization_id, context)
    try:
        result = use_case.execute(
            invite_member_request_to_command(
                OrganizationId(organization_id),
                UserId(context.user_id),
                payload,
            )
        )
    except Exception as exc:
        raise map_membership_flow_error(exc) from exc

    return invite_member_result_to_response(result)


@router.post(
    "/memberships/invites/accept",
    response_model=AcceptMembershipInviteResponse,
    responses={
        403: {"model": ErrorResponse},
        410: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def accept_membership_invite(
    payload: AcceptMembershipInviteRequest,
    claims: AccessTokenClaims = Depends(get_access_token_claims),
    use_case: AcceptMembershipInviteUseCase = Depends(get_accept_membership_invite_use_case),
) -> AcceptMembershipInviteResponse:
    try:
        result = use_case.execute(
            accept_membership_invite_request_to_command(payload, UserId(claims.sub.value))
        )
    except InactiveUserError as exc:
        raise map_membership_flow_error(exc) from exc
    except Exception as exc:
        raise map_membership_flow_error(exc) from exc

    return accept_membership_invite_result_to_response(result)


@router.post(
    "/memberships/{membership_id}/suspend",
    response_model=MembershipResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def suspend_membership(
    scoped_membership_id: MembershipId = Depends(require_scoped_membership("identity.memberships.update")),
    use_case: SuspendMembershipUseCase = Depends(get_suspend_membership_use_case),
) -> MembershipResponse:
    try:
        result = use_case.execute(suspend_membership_command(scoped_membership_id))
    except MembershipError as exc:
        raise map_membership_error(exc) from exc

    return membership_result_to_response(result)


@router.delete(
    "/memberships/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def remove_membership(
    scoped_membership_id: MembershipId = Depends(require_scoped_membership("identity.memberships.remove")),
    use_case: RemoveMembershipUseCase = Depends(get_remove_membership_use_case),
) -> Response:
    try:
        use_case.execute(remove_membership_command(scoped_membership_id))
    except MembershipError as exc:
        raise map_membership_error(exc) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
