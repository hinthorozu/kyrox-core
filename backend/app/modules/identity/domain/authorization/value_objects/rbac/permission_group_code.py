import re
from dataclasses import dataclass

_PERMISSION_GROUP_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)?$")


@dataclass(frozen=True, slots=True)
class PermissionGroupCode:
    value: str

    @classmethod
    def create(cls, raw: str) -> "PermissionGroupCode":
        normalized = raw.strip().lower()
        if not normalized or not _PERMISSION_GROUP_CODE_PATTERN.match(normalized):
            raise ValueError("Invalid permission group code")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Permission group code cannot be empty")
