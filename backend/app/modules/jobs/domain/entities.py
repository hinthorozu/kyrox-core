from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.jobs.domain.value_objects.failure_reason import FailureReason
from app.modules.jobs.domain.value_objects.job_status import JobStatus
from app.modules.jobs.domain.value_objects.job_type import JobType

JsonPayload = dict[str, Any]
JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


@dataclass(slots=True)
class Job:
    id: UUID
    organization_id: UUID
    job_type: JobType
    payload: JsonPayload
    status: JobStatus
    idempotency_key: str | None
    attempt_count: int
    max_attempts: int
    result: JsonValue | None
    failure_reason: FailureReason | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
