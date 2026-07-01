import re
from dataclasses import dataclass

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class InviteEmail:
    value: str

    @classmethod
    def create(cls, raw: str) -> "InviteEmail":
        normalized = raw.strip().lower()
        if not normalized or not _EMAIL_PATTERN.match(normalized):
            raise ValueError("Invalid invite email address")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Invite email cannot be empty")
