import uuid
from datetime import UTC, datetime

import pytest

from app.modules.jobs.application.commands import EnqueueJobCommand, GetJobCommand
from app.modules.jobs.application.enqueue_job import EnqueueJobUseCase
from app.modules.jobs.application.get_job import GetJobUseCase
from app.modules.jobs.domain.entities import Job
from app.modules.jobs.domain.exceptions import DuplicateIdempotencyConflictError, JobNotFoundError
from app.modules.jobs.domain.value_objects.job_status import JobStatus
from app.modules.jobs.domain.value_objects.job_type import JobType


class FakeJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, Job] = {}

    def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        return self._jobs.get(job_id)

    def find_by_idempotency(self, organization_id, job_type, idempotency_key):
        for job in self._jobs.values():
            if (
                job.organization_id == organization_id
                and job.job_type.value == job_type.value
                and job.idempotency_key == idempotency_key
            ):
                return job
        return None

    def save(self, job: Job) -> Job:
        self._jobs[job.id] = job
        return job

    def list_pending(self, *, limit: int) -> list[Job]:
        return [job for job in self._jobs.values() if job.status is JobStatus.PENDING][:limit]

    def claim_pending(self, job_id: uuid.UUID) -> Job | None:
        return None

    def claim_next_pending(self, *, limit: int) -> list[Job]:
        return []


def test_enqueue_job_returns_existing_idempotent_job() -> None:
    repo = FakeJobRepository()
    org_id = uuid.uuid4()
    use_case = EnqueueJobUseCase(repo)
    command = EnqueueJobCommand(
        organization_id=org_id,
        job_type="core.platform.echo",
        payload={"value": 1},
        idempotency_key="job-1",
    )

    first = use_case.execute(command)
    second = use_case.execute(command)

    assert first.created is True
    assert second.created is False
    assert first.job.id == second.job.id


def test_enqueue_job_rejects_conflicting_idempotency_payload() -> None:
    repo = FakeJobRepository()
    org_id = uuid.uuid4()
    use_case = EnqueueJobUseCase(repo)
    use_case.execute(
        EnqueueJobCommand(
            organization_id=org_id,
            job_type="core.platform.echo",
            payload={"value": 1},
            idempotency_key="job-1",
        )
    )

    with pytest.raises(DuplicateIdempotencyConflictError):
        use_case.execute(
            EnqueueJobCommand(
                organization_id=org_id,
                job_type="core.platform.echo",
                payload={"value": 2},
                idempotency_key="job-1",
            )
        )


def test_get_job_use_case_masks_other_org() -> None:
    repo = FakeJobRepository()
    org_id = uuid.uuid4()
    other_org_id = uuid.uuid4()
    job_id = uuid.uuid4()
    now = datetime.now(UTC)
    repo.save(
        Job(
            id=job_id,
            organization_id=other_org_id,
            job_type=JobType.create("core.platform.echo"),
            payload={"value": 1},
            status=JobStatus.PENDING,
            idempotency_key=None,
            attempt_count=0,
            max_attempts=3,
            result=None,
            failure_reason=None,
            created_at=now,
            started_at=None,
            finished_at=None,
        )
    )

    with pytest.raises(JobNotFoundError):
        GetJobUseCase(repo).execute(GetJobCommand(job_id=job_id, organization_id=org_id))
