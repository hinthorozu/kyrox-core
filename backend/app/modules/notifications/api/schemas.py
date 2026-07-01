from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SendNotificationRequest(BaseModel):
    channel: str
    recipient: str
    subject: str
    body: str
    template_key: str | None = None
    variables: dict[str, Any] | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    channel: str
    recipient: str
    subject: str
    status: str
    template_key: str | None
    job_id: UUID | None
    failure_reason: str | None
    failure_code: str | None
    created_at: datetime
    queued_at: datetime | None
    sent_at: datetime | None
    failed_at: datetime | None
    suppressed_at: datetime | None


class SendNotificationResponse(BaseModel):
    notification: NotificationResponse
    created: bool


class ErrorResponse(BaseModel):
    detail: str
