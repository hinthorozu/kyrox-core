import re
from dataclasses import dataclass

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    @classmethod
    def create(cls, raw: str) -> "Email":
        normalized = raw.strip().lower()
        if not normalized or not _EMAIL_PATTERN.match(normalized):
            raise ValueError("Invalid email address")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Email value cannot be empty")
