from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.exceptions import InvalidRoleError
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import OrganizationId
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
    role_kind: str = "organization"
    organization_id: OrganizationId | None = None
    source_template_role_id: RoleId | None = None
    template_version: int = 1
    source_template_version: int | None = None
    permissions_customized: bool = False
    is_assignable: bool = True
    is_protected: bool = False
    auto_include_new_permissions: bool = False

    def is_active(self) -> bool:
        return self.deleted_at is None

    def assert_active(self) -> None:
        if not self.is_active():
            raise InvalidRoleError("Role is not active")
