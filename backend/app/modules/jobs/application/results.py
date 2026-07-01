from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class JobResult:
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
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class EnqueueJobResult:
    job: JobResult
    created: bool
