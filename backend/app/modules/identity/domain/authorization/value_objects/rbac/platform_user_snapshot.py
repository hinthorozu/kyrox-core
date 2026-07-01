from dataclasses import dataclass

from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId


@dataclass(frozen=True, slots=True)
class PlatformUserSnapshot:
    user_id: UserId
    is_active: bool
    is_super_admin: bool
    is_deleted: bool

    def can_be_authorized(self) -> bool:
        return self.is_active and not self.is_deleted
