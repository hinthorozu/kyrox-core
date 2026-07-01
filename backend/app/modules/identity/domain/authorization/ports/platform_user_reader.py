from typing import Protocol

from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.value_objects.rbac.platform_user_snapshot import (
    PlatformUserSnapshot,
)


class PlatformUserReader(Protocol):
    def get_snapshot(self, user_id: UserId) -> PlatformUserSnapshot | None: ...
