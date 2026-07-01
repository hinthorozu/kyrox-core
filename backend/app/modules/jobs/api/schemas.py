from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EnqueueJobRequest(BaseModel):
    job_type: str
    payload: dict[str, Any]
    idempotency_key: str | None = None
    max_attempts: int | None = Field(default=None, ge=1, le=10)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    job_type: str
    status: str
    payload: dict[str, Any]
    idempotency_key: str | None
    attempt_count: int
    max_attempts: int
    result: Any | None
    failure_reason: str | None
    failure_code: str | None
    created_at: Any
    started_at: Any | None
    finished_at: Any | None


class EnqueueJobResponse(BaseModel):
    job: JobResponse
    created: bool


class ErrorResponse(BaseModel):
    detail: str
