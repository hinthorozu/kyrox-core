from typing import Protocol

from app.modules.identity.domain.authorization.entities.role import Role
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug


class RoleRepository(Protocol):
    def add(self, role: Role) -> Role: ...

    def update(self, role: Role) -> Role: ...

    def remove(self, role_id: RoleId) -> None: ...

    def get_by_id(self, role_id: RoleId) -> Role | None: ...

    def get_by_slug(self, slug: RoleSlug, scope: RoleScope) -> Role | None: ...

    def list_system_roles(self) -> list[Role]: ...
