from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PermissionGroupId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("PermissionGroupId value must be a UUID")
