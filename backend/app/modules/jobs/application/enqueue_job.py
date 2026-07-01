from datetime import UTC, datetime
from uuid import uuid4

from app.modules.jobs.application.commands import EnqueueJobCommand
from app.modules.jobs.application.job_result_mapper import to_job_result
from app.modules.jobs.application.policy import JobPolicy
from app.modules.jobs.application.results import EnqueueJobResult
from app.modules.jobs.domain.entities import Job
from app.modules.jobs.domain.exceptions import DuplicateIdempotencyConflictError
from app.modules.jobs.domain.ports import JobRepository
from app.modules.jobs.domain.value_objects.job_status import JobStatus


class EnqueueJobUseCase:
    def __init__(
        self,
        job_repository: JobRepository,
        job_policy: JobPolicy | None = None,
    ) -> None:
        self._job_repository = job_repository
        self._job_policy = job_policy or JobPolicy()

    def execute(self, command: EnqueueJobCommand) -> EnqueueJobResult:
        job_type = self._job_policy.normalize_job_type(command.job_type)
        payload = self._job_policy.validate_payload(command.payload)
        idempotency_key = self._job_policy.normalize_idempotency_key(command.idempotency_key)
        max_attempts = self._job_policy.normalize_max_attempts(command.max_attempts)

        if idempotency_key is not None:
            existing = self._job_repository.find_by_idempotency(
                command.organization_id,
                job_type,
                idempotency_key,
            )
            if existing is not None:
                if not self._job_policy.payloads_match(existing.payload, payload):
                    raise DuplicateIdempotencyConflictError(
                        "Idempotency key already used with a different payload"
                    )
                return EnqueueJobResult(job=to_job_result(existing), created=False)

        now = datetime.now(UTC)
        job = Job(
            id=uuid4(),
            organization_id=command.organization_id,
            job_type=job_type,
            payload=payload,
            status=JobStatus.PENDING,
            idempotency_key=idempotency_key,
            attempt_count=0,
            max_attempts=max_attempts,
            result=None,
            failure_reason=None,
            created_at=now,
            started_at=None,
            finished_at=None,
        )
        saved = self._job_repository.save(job)
        return EnqueueJobResult(job=to_job_result(saved), created=True)
