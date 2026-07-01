from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.authorization.exceptions import InvalidPermissionError
from app.modules.identity.domain.authorization.value_objects.identity.permission_group_id import (
    PermissionGroupId,
)
from app.modules.identity.domain.authorization.value_objects.rbac.permission_group_code import (
    PermissionGroupCode,
)
from app.modules.identity.domain.authorization.value_objects.rbac.permission_module import (
    PermissionModule,
)


@dataclass
class PermissionGroup:
    id: PermissionGroupId
    code: PermissionGroupCode
    name: str
    module: PermissionModule
    description: str
    sort_order: int
    is_system: bool
    created_at: datetime
    updated_at: datetime

    def assert_modifiable(self) -> None:
        if self.is_system:
            raise InvalidPermissionError("System permission groups cannot be modified")
