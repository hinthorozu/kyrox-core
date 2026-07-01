from dataclasses import dataclass

from app.modules.notifications.domain.exceptions import InvalidNotificationRequestError

_MAX_RECIPIENT_LENGTH = 320


@dataclass(frozen=True, slots=True)
class Recipient:
    value: str

    @classmethod
    def create(cls, raw: str) -> "Recipient":
        normalized = raw.strip()
        if not normalized:
            raise InvalidNotificationRequestError("Recipient cannot be empty")
        if len(normalized) > _MAX_RECIPIENT_LENGTH:
            raise InvalidNotificationRequestError(
                f"Recipient exceeds maximum length of {_MAX_RECIPIENT_LENGTH} characters"
            )
        return cls(value=normalized)
