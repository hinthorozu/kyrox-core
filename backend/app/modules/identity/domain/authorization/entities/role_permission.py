from dataclasses import dataclass

from app.modules.identity.domain.authorization.value_objects.identity.permission_id import PermissionId
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId


@dataclass(frozen=True, slots=True)
class RolePermission:
    role_id: RoleId
    permission_id: PermissionId
