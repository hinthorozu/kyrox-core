from typing import Protocol
from uuid import UUID

from app.modules.settings.domain.entities import Setting
from app.modules.settings.domain.value_objects.setting_key import SettingKey
from app.modules.settings.domain.value_objects.setting_scope import SettingScope


class SettingRepository(Protocol):
    def get(
        self,
        scope: SettingScope,
        organization_id: UUID | None,
        key: SettingKey,
    ) -> Setting | None: ...

    def list_by_scope(
        self,
        scope: SettingScope,
        organization_id: UUID | None,
        *,
        key_prefix: str | None = None,
    ) -> list[Setting]: ...

    def upsert(self, setting: Setting) -> Setting: ...

    def delete(
        self,
        scope: SettingScope,
        organization_id: UUID | None,
        key: SettingKey,
    ) -> bool: ...
