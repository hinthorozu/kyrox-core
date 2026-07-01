from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.jobs.domain.entities import Job, JsonValue
from app.modules.jobs.domain.value_objects.job_type import JobType


class JobRepository(Protocol):
    def get_by_id(self, job_id: UUID) -> Job | None: ...

    def find_by_idempotency(
        self,
        organization_id: UUID,
        job_type: JobType,
        idempotency_key: str,
    ) -> Job | None: ...

    def save(self, job: Job) -> Job: ...

    def list_pending(self, *, limit: int) -> list[Job]: ...

    def claim_pending(self, job_id: UUID) -> Job | None: ...

    def claim_next_pending(self, *, limit: int) -> list[Job]: ...


@dataclass(frozen=True, slots=True)
class JobHandlerResult:
    result: JsonValue | None = None
    retryable: bool = True


class JobHandler(Protocol):
    def handle(self, job: Job) -> JobHandlerResult: ...


class JobHandlerRegistry(Protocol):
    def register(self, job_type: JobType, handler: JobHandler) -> None: ...

    def get(self, job_type: JobType) -> JobHandler | None: ...
