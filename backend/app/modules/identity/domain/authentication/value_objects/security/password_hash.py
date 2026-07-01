from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PasswordHash:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("PasswordHash value cannot be empty")
