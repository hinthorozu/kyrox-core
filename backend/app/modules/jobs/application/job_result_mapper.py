from app.modules.jobs.application.results import JobResult
from app.modules.jobs.domain.entities import Job


def to_job_result(job: Job) -> JobResult:
    return JobResult(
        id=job.id,
        organization_id=job.organization_id,
        job_type=job.job_type.value,
        status=job.status.value,
        payload=job.payload,
        idempotency_key=job.idempotency_key,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        result=job.result,
        failure_reason=job.failure_reason.message if job.failure_reason else None,
        failure_code=job.failure_reason.code if job.failure_reason else None,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )
