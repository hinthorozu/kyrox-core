from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PermissionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("PermissionId value must be a UUID")
