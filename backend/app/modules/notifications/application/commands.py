from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SendNotificationCommand:
    organization_id: UUID
    channel: str
    recipient: str
    subject: str
    body: str
    template_key: str | None = None
    variables: dict[str, Any] | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class GetNotificationCommand:
    notification_id: UUID
    organization_id: UUID


@dataclass(frozen=True, slots=True)
class DispatchNotificationCommand:
    notification_id: UUID
