from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MembershipId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("MembershipId value must be a UUID")
