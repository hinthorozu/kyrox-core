from typing import Protocol

from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.value_objects.rbac.permission_code import PermissionCode


class PermissionChecker(Protocol):
    def has_permission(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
        permission_code: PermissionCode,
    ) -> bool: ...
