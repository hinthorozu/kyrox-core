from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.settings.domain.value_objects.setting_scope import SettingScope


@dataclass(frozen=True, slots=True)
class GetSettingCommand:
    scope: SettingScope
    organization_id: UUID | None
    key: str


@dataclass(frozen=True, slots=True)
class ListSettingsCommand:
    scope: SettingScope
    organization_id: UUID | None
    key_prefix: str | None = None


@dataclass(frozen=True, slots=True)
class UpsertSettingCommand:
    scope: SettingScope
    organization_id: UUID | None
    key: str
    value: Any


@dataclass(frozen=True, slots=True)
class DeleteSettingCommand:
    scope: SettingScope
    organization_id: UUID | None
    key: str
