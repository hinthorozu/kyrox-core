from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus


@dataclass(frozen=True, slots=True)
class SendNotificationResult:
    notification_id: UUID
    organization_id: UUID
    channel: NotificationChannel
    recipient: str
    subject: str
    template_key: str | None
    status: NotificationStatus
    job_id: UUID | None
    failure_reason: str | None
    failure_code: str | None
    idempotent_replay: bool
    created_at: datetime
    queued_at: datetime | None
    sent_at: datetime | None
    failed_at: datetime | None
    suppressed_at: datetime | None


@dataclass(frozen=True, slots=True)
class GetNotificationResult:
    notification_id: UUID
    organization_id: UUID
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    template_key: str | None
    variables: dict[str, Any] | None
    status: NotificationStatus
    job_id: UUID | None
    failure_reason: str | None
    failure_code: str | None
    created_at: datetime
    queued_at: datetime | None
    sent_at: datetime | None
    failed_at: datetime | None
    suppressed_at: datetime | None


@dataclass(frozen=True, slots=True)
class DispatchNotificationResult:
    notification_id: UUID
    status: NotificationStatus
    idempotent_noop: bool
