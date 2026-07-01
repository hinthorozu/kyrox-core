from typing import Protocol

from app.modules.identity.domain.authorization.entities.organization_role import OrganizationRole
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.organization_role_id import (
    OrganizationRoleId,
)
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId


class OrganizationRoleRepository(Protocol):
    def add(self, organization_role: OrganizationRole) -> OrganizationRole: ...

    def update(self, organization_role: OrganizationRole) -> OrganizationRole: ...

    def remove(self, organization_role_id: OrganizationRoleId) -> None: ...

    def get_by_id(self, organization_role_id: OrganizationRoleId) -> OrganizationRole | None: ...

    def get_by_organization_and_role(
        self,
        organization_id: OrganizationId,
        role_id: RoleId,
    ) -> OrganizationRole | None: ...

    def list_active_by_organization(
        self,
        organization_id: OrganizationId,
    ) -> list[OrganizationRole]: ...
