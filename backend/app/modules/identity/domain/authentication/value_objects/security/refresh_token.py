from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RefreshToken:
    value: str

    @classmethod
    def create(cls, raw: str) -> "RefreshToken":
        normalized = raw.strip()
        if not normalized:
            raise ValueError("Refresh token cannot be empty")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Refresh token cannot be empty")
