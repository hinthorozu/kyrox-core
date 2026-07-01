import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.settings.domain.entities import JsonValue, Setting
from app.modules.settings.domain.exceptions import (
    InvalidSettingKeyError,
    InvalidSettingScopeError,
    InvalidSettingValueError,
)
from app.modules.settings.domain.value_objects.setting_key import SettingKey
from app.modules.settings.domain.value_objects.setting_scope import SettingScope

MAX_SETTING_VALUE_BYTES = 65536
_MIN_KEY_PREFIX_LENGTH = 3


@dataclass(frozen=True, slots=True)
class SettingPolicy:
    max_value_bytes: int = MAX_SETTING_VALUE_BYTES
    min_key_prefix_length: int = _MIN_KEY_PREFIX_LENGTH

    def validate_scope(self, scope: SettingScope, organization_id: UUID | None) -> None:
        if scope == SettingScope.ORGANIZATION and organization_id is None:
            raise InvalidSettingScopeError(
                "organization_id is required when scope is organization"
            )
        if scope == SettingScope.SYSTEM and organization_id is not None:
            raise InvalidSettingScopeError(
                "organization_id must be null when scope is system"
            )

    def normalize_key(self, raw: str) -> SettingKey:
        return SettingKey.create(raw)

    def validate_key_prefix(self, key_prefix: str | None) -> str | None:
        if key_prefix is None:
            return None
        normalized = key_prefix.strip().lower()
        if not normalized:
            raise InvalidSettingKeyError("key_prefix cannot be empty")
        if len(normalized) < self.min_key_prefix_length:
            raise InvalidSettingKeyError(
                f"key_prefix must be at least {self.min_key_prefix_length} characters"
            )
        return normalized

    def validate_value(self, value: Any) -> JsonValue:
        if value is None:
            raise InvalidSettingValueError(
                "Setting value cannot be null; use DELETE to remove a setting"
            )
        try:
            serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise InvalidSettingValueError("Setting value must be JSON-serializable") from exc
        encoded_size = len(serialized.encode("utf-8"))
        if encoded_size > self.max_value_bytes:
            raise InvalidSettingValueError(
                f"Setting value exceeds maximum size of {self.max_value_bytes} bytes"
            )
        return value
