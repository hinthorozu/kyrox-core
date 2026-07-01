from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogListQueryParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    action: str | None = None
    action_prefix: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    user_id: UUID | None = None
    session_id: UUID | None = None
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None
    limit: int = 50
    cursor: str | None = None


class AuditLogResponse(BaseModel):
    id: UUID
    organization_id: UUID | None
    user_id: UUID | None
    session_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    old_values: dict | None
    new_values: dict | None
    metadata: dict | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    next_cursor: str | None


class ErrorResponse(BaseModel):
    detail: str


class RecordAuditEventRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=255)
    resource_type: str = Field(..., min_length=1, max_length=128)
    resource_id: str | None = Field(default=None, max_length=255)
    old_values: dict | None = None
    new_values: dict | None = None
    metadata: dict | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=512)
