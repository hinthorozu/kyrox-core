from dataclasses import dataclass


_MAX_USER_AGENT_LENGTH = 512


@dataclass(frozen=True, slots=True)
class UserAgent:
    value: str

    @classmethod
    def create(cls, raw: str) -> "UserAgent":
        normalized = raw.strip()
        if not normalized:
            raise ValueError("User agent cannot be empty")
        if len(normalized) > _MAX_USER_AGENT_LENGTH:
            raise ValueError("User agent exceeds maximum length")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("User agent cannot be empty")
        if len(self.value) > _MAX_USER_AGENT_LENGTH:
            raise ValueError("User agent exceeds maximum length")
