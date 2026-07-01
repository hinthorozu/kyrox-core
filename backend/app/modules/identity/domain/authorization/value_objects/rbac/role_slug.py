import re
from dataclasses import dataclass

_ROLE_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,63}$")


@dataclass(frozen=True, slots=True)
class RoleSlug:
    value: str

    @classmethod
    def create(cls, raw: str) -> "RoleSlug":
        normalized = raw.strip().lower()
        if not normalized or not _ROLE_SLUG_PATTERN.match(normalized):
            raise ValueError("Invalid role slug")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Role slug cannot be empty")
