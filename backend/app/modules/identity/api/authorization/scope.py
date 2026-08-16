from uuid import UUID

from app.core.exceptions import AppException
from app.modules.identity.api.authorization.context import (
    AuthenticatedOrganizationContext,
    AuthorizationContext,
)


def assert_organization_scope(
    path_organization_id: UUID,
    context: AuthorizationContext | AuthenticatedOrganizationContext,
) -> None:
    """Ensure a path organization matches the authenticated organization context."""
    if context.is_super_admin:
        return
    if path_organization_id != context.organization_id:
        raise AppException("Organization scope mismatch", status_code=400)
