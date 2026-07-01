from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.notifications.domain.value_objects.failure_reason import FailureReason
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus
from app.modules.notifications.domain.value_objects.recipient import Recipient


@dataclass(slots=True)
class Notification:
    id: UUID
    organization_id: UUID
    channel: NotificationChannel
    recipient: Recipient
    subject: str
    body: str
    template_key: str | None
    variables: dict[str, Any] | None
    status: NotificationStatus
    idempotency_key: str | None
    job_id: UUID | None
    failure_reason: FailureReason | None
    created_at: datetime
    queued_at: datetime | None
    sent_at: datetime | None
    failed_at: datetime | None
    suppressed_at: datetime | None
