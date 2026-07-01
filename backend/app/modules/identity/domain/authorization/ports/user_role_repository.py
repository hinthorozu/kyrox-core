from typing import Protocol

from app.modules.identity.domain.authorization.entities.user_role import UserRole
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.value_objects.identity.user_role_id import UserRoleId


class UserRoleRepository(Protocol):
    def add(self, user_role: UserRole) -> UserRole: ...

    def update(self, user_role: UserRole) -> UserRole: ...

    def remove(self, user_role_id: UserRoleId) -> None: ...

    def get_by_id(self, user_role_id: UserRoleId) -> UserRole | None: ...

    def list_effective_by_user_and_organization(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> list[UserRole]: ...

    def revoke(self, user_role_id: UserRoleId) -> None: ...
