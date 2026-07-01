import re
from dataclasses import dataclass

_PERMISSION_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$")


@dataclass(frozen=True, slots=True)
class PermissionCode:
    value: str

    @classmethod
    def create(cls, raw: str) -> "PermissionCode":
        normalized = raw.strip().lower()
        if not normalized or not _PERMISSION_CODE_PATTERN.match(normalized):
            raise ValueError("Invalid permission code")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Permission code cannot be empty")
