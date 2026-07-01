from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenHash:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("TokenHash value cannot be empty")
