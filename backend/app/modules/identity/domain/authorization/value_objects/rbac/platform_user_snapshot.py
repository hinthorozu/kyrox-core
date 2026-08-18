from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId


@dataclass(frozen=True, slots=True)
class PlatformUserSnapshot:
    user_id: UserId
    is_active: bool
    is_super_admin: bool
    is_deleted: bool
    organization_id: UUID | None = None

    def can_be_authorized(self) -> bool:
        return self.is_active and not self.is_deleted
