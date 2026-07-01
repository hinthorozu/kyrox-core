from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SettingUpsertRequest(BaseModel):
    value: Any


class SettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope: str
    organization_id: UUID | None
    key: str
    value: Any
    created_at: datetime
    updated_at: datetime


class SettingListResponse(BaseModel):
    items: list[SettingResponse]


class ErrorResponse(BaseModel):
    detail: str
