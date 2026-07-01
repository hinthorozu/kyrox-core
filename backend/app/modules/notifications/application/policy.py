import re
from typing import Any

from app.modules.notifications.domain.exceptions import (
    InvalidNotificationRequestError,
    UnsupportedNotificationChannelError,
)
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.recipient import Recipient

_MAX_SUBJECT_LENGTH = 998
_MAX_BODY_LENGTH = 1_000_000
_MAX_TEMPLATE_KEY_LENGTH = 128
_MAX_IDEMPOTENCY_KEY_LENGTH = 128
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class NotificationPolicy:
    def normalize_channel(self, raw: str) -> NotificationChannel:
        normalized = raw.strip().lower()
        try:
            channel = NotificationChannel(normalized)
        except ValueError as exc:
            raise UnsupportedNotificationChannelError(
                f"Unsupported notification channel: {raw}"
            ) from exc
        return channel

    def normalize_recipient(self, raw: str, channel: NotificationChannel) -> Recipient:
        recipient = Recipient.create(raw)
        if channel == NotificationChannel.EMAIL and not _EMAIL_PATTERN.match(recipient.value):
            raise InvalidNotificationRequestError("Recipient must be a valid email address")
        return recipient

    def normalize_subject(self, raw: str) -> str:
        normalized = raw.strip()
        if not normalized:
            raise InvalidNotificationRequestError("Subject cannot be empty")
        if len(normalized) > _MAX_SUBJECT_LENGTH:
            raise InvalidNotificationRequestError(
                f"Subject exceeds maximum length of {_MAX_SUBJECT_LENGTH} characters"
            )
        return normalized

    def normalize_body(self, raw: str) -> str:
        normalized = raw.strip()
        if not normalized:
            raise InvalidNotificationRequestError("Body cannot be empty")
        if len(normalized) > _MAX_BODY_LENGTH:
            raise InvalidNotificationRequestError(
                f"Body exceeds maximum length of {_MAX_BODY_LENGTH} characters"
            )
        return normalized

    def normalize_template_key(self, raw: str | None) -> str | None:
        if raw is None:
            return None
        normalized = raw.strip()
        if not normalized:
            return None
        if len(normalized) > _MAX_TEMPLATE_KEY_LENGTH:
            raise InvalidNotificationRequestError(
                f"Template key exceeds maximum length of {_MAX_TEMPLATE_KEY_LENGTH} characters"
            )
        return normalized

    def normalize_idempotency_key(self, raw: str | None) -> str | None:
        if raw is None:
            return None
        normalized = raw.strip()
        if not normalized:
            return None
        if len(normalized) > _MAX_IDEMPOTENCY_KEY_LENGTH:
            raise InvalidNotificationRequestError(
                f"Idempotency key exceeds maximum length of {_MAX_IDEMPOTENCY_KEY_LENGTH} characters"
            )
        return normalized

    def normalize_variables(self, raw: dict[str, Any] | None) -> dict[str, Any] | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise InvalidNotificationRequestError("Variables must be a JSON object")
        return raw

    def payloads_match(
        self,
        *,
        channel: NotificationChannel,
        recipient: Recipient,
        subject: str,
        body: str,
        template_key: str | None,
        existing_channel: NotificationChannel,
        existing_recipient: Recipient,
        existing_subject: str,
        existing_body: str,
        existing_template_key: str | None,
    ) -> bool:
        return (
            channel == existing_channel
            and recipient.value == existing_recipient.value
            and subject == existing_subject
            and body == existing_body
            and template_key == existing_template_key
        )
