import logging

from app.modules.notifications.domain.exceptions import NotificationDispatchError
from app.modules.notifications.domain.ports import (
    ChannelDispatchRequest,
    ChannelDispatchResult,
    NotificationChannelAdapter,
)

logger = logging.getLogger(__name__)


def redact_recipient(value: str) -> str:
    if "@" not in value:
        return "***"
    local, domain = value.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


class EmailLogStubAdapter(NotificationChannelAdapter):
    def __init__(self, *, fail_next: bool = False) -> None:
        self._fail_next = fail_next

    def send(self, request: ChannelDispatchRequest) -> ChannelDispatchResult:
        if self._fail_next:
            self._fail_next = False
            raise NotificationDispatchError("Simulated email dispatch failure")

        logger.info(
            "notification email stub dispatch",
            extra={
                "notification_id": str(request.notification_id),
                "organization_id": str(request.organization_id),
                "channel": request.channel.value,
                "recipient_redacted": redact_recipient(request.recipient.value),
                "subject_length": len(request.subject),
                "body_length": len(request.body),
                "template_key": request.template_key,
            },
        )
        return ChannelDispatchResult(
            provider_message_id=f"stub-{request.notification_id}",
        )
