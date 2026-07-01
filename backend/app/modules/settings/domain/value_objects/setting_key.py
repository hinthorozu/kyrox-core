import re
from dataclasses import dataclass

from app.modules.settings.domain.exceptions import InvalidSettingKeyError

_SETTING_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2,}$")
_MAX_KEY_LENGTH = 255


@dataclass(frozen=True, slots=True)
class SettingKey:
    value: str

    @classmethod
    def create(cls, raw: str) -> "SettingKey":
        normalized = raw.strip().lower()
        if not normalized:
            raise InvalidSettingKeyError("Setting key cannot be empty")
        if len(normalized) > _MAX_KEY_LENGTH:
            raise InvalidSettingKeyError(
                f"Setting key exceeds maximum length of {_MAX_KEY_LENGTH} characters"
            )
        if not _SETTING_KEY_PATTERN.match(normalized):
            raise InvalidSettingKeyError(
                "Setting key must be lowercase dot-separated with at least three segments"
            )
        return cls(value=normalized)
