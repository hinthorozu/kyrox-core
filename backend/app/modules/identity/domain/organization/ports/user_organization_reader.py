from typing import Protocol

from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


class UserOrganizationReader(Protocol):
    """Read the single organization directly assigned to a platform user."""

    def get_organization_id(self, user_id: UserId) -> OrganizationId | None: ...
