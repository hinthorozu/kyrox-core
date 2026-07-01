from app.core.exceptions import AppException
from app.modules.identity.domain.authentication.exceptions import InactiveUserError
from app.modules.identity.domain.authorization.exceptions import InvalidRoleError
from app.modules.identity.domain.organization.exceptions import (
    DuplicateOrganizationSlugError,
    InactiveOrganizationError,
    InvalidOrganizationSlugError,
    OrganizationError,
    OrganizationNotFoundError,
)


def map_organization_error(exc: OrganizationError) -> AppException:
    if isinstance(exc, OrganizationNotFoundError):
        return AppException(str(exc), status_code=404)
    if isinstance(exc, DuplicateOrganizationSlugError):
        return AppException(str(exc), status_code=409)
    if isinstance(exc, InactiveOrganizationError):
        return AppException(str(exc), status_code=409)
    if isinstance(exc, InvalidOrganizationSlugError):
        return AppException(str(exc), status_code=422)
    return AppException(str(exc), status_code=400)


def map_create_organization_error(exc: Exception) -> AppException:
    if isinstance(exc, InactiveUserError):
        return AppException(str(exc), status_code=403)
    if isinstance(exc, OrganizationError):
        return map_organization_error(exc)
    if isinstance(exc, InvalidRoleError):
        return AppException("Required organization roles are not seeded", status_code=503)
    return AppException(str(exc), status_code=400)
