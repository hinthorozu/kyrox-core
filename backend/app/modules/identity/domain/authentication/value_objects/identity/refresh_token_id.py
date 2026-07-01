from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RefreshTokenId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("RefreshTokenId value must be a UUID")
