from dataclasses import dataclass

from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId


@dataclass(frozen=True, slots=True)
class CheckPermissionCommand:
    user_id: UserId
    organization_id: OrganizationId
    permission_code: str
