from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InviteTokenHash:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Invite token hash cannot be empty")
