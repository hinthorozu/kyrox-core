from typing import Protocol
from uuid import UUID

from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


class UserOrganizationReader(Protocol):
    """Read the single organization directly assigned to a platform user."""

    def get_organization_id(self, user_id: UUID) -> OrganizationId | None: ...
