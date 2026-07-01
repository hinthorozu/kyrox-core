from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("SessionId value must be a UUID")
