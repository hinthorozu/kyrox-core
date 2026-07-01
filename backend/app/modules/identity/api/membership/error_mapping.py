from app.core.exceptions import AppException
from app.modules.identity.domain.authorization.exceptions import InvalidRoleError
from app.modules.identity.domain.membership.exceptions import (
    DuplicateMembershipError,
    InvalidMembershipTransitionError,
    MembershipError,
    MembershipInviteAlreadyAcceptedError,
    MembershipInviteExpiredError,
    MembershipNotFoundError,
)
from app.modules.identity.domain.organization.exceptions import OrganizationError, OrganizationNotFoundError


def map_membership_error(exc: MembershipError) -> AppException:
    if isinstance(exc, MembershipNotFoundError):
        return AppException(str(exc), status_code=404)
    if isinstance(exc, DuplicateMembershipError):
        return AppException(str(exc), status_code=409)
    if isinstance(exc, InvalidMembershipTransitionError):
        return AppException(str(exc), status_code=409)
    if isinstance(exc, MembershipInviteExpiredError):
        return AppException(str(exc), status_code=410)
    if isinstance(exc, MembershipInviteAlreadyAcceptedError):
        return AppException(str(exc), status_code=409)
    return AppException(str(exc), status_code=400)


def map_membership_flow_error(exc: Exception) -> AppException:
    if isinstance(exc, MembershipError):
        return map_membership_error(exc)
    if isinstance(exc, OrganizationNotFoundError):
        return AppException(str(exc), status_code=404)
    if isinstance(exc, OrganizationError):
        return AppException(str(exc), status_code=400)
    if isinstance(exc, InvalidRoleError):
        return AppException("Required organization roles are not seeded", status_code=503)
    return AppException(str(exc), status_code=400)
