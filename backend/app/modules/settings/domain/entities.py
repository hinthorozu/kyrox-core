from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.settings.domain.value_objects.setting_key import SettingKey
from app.modules.settings.domain.value_objects.setting_scope import SettingScope

JsonValue = dict[str, Any] | list[Any] | str | int | float | bool


@dataclass(frozen=True, slots=True)
class Setting:
    id: UUID
    scope: SettingScope
    organization_id: UUID | None
    key: SettingKey
    value: JsonValue
    created_at: datetime
    updated_at: datetime
