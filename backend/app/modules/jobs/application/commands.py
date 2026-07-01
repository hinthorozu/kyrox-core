from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EnqueueJobCommand:
    organization_id: UUID
    job_type: str
    payload: dict[str, Any]
    idempotency_key: str | None = None
    max_attempts: int | None = None


@dataclass(frozen=True, slots=True)
class GetJobCommand:
    job_id: UUID
    organization_id: UUID


@dataclass(frozen=True, slots=True)
class ProcessPendingJobsCommand:
    limit: int = 10
