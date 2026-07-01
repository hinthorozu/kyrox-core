from typing import Protocol

from app.modules.identity.domain.authorization.entities.role_permission import RolePermission
from app.modules.identity.domain.authorization.value_objects.identity.permission_id import PermissionId
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId


class RolePermissionRepository(Protocol):
    def grant(self, role_permission: RolePermission) -> None: ...

    def revoke(self, role_id: RoleId, permission_id: PermissionId) -> None: ...

    def list_permission_ids_for_role(self, role_id: RoleId) -> list[PermissionId]: ...

    def has_permission(self, role_id: RoleId, permission_id: PermissionId) -> bool: ...
