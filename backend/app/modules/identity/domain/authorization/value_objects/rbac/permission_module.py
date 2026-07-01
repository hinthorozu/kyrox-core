from dataclasses import dataclass

_ALLOWED_MODULES = frozenset({"audit", "core", "identity", "settings"})


@dataclass(frozen=True, slots=True)
class PermissionModule:
    value: str

    @classmethod
    def create(cls, raw: str) -> "PermissionModule":
        normalized = raw.strip().lower()
        if normalized not in _ALLOWED_MODULES:
            raise ValueError("Invalid permission module")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Permission module cannot be empty")
