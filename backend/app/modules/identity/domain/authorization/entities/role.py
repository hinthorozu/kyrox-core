from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.exceptions import InvalidRoleError
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug


@dataclass
class Role:
    id: RoleId
    name: str
    slug: RoleSlug
    scope: RoleScope
    is_system: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    def is_active(self) -> bool:
        return self.deleted_at is None

    def assert_active(self) -> None:
        if not self.is_active():
            raise InvalidRoleError("Role is not active")
