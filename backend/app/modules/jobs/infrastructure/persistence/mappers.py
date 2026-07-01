from app.modules.jobs.domain.entities import Job
from app.modules.jobs.domain.value_objects.failure_reason import FailureReason
from app.modules.jobs.domain.value_objects.job_status import JobStatus
from app.modules.jobs.domain.value_objects.job_type import JobType
from app.modules.jobs.infrastructure.persistence.models import PlatformJobModel


def job_to_domain(model: PlatformJobModel) -> Job:
    failure_reason = None
    if model.failure_reason is not None:
        failure_reason = FailureReason(message=model.failure_reason, code=model.failure_code)

    return Job(
        id=model.id,
        organization_id=model.organization_id,
        job_type=JobType(value=model.job_type),
        payload=model.payload,
        status=JobStatus(model.status),
        idempotency_key=model.idempotency_key,
        attempt_count=model.attempt_count,
        max_attempts=model.max_attempts,
        result=model.result,
        failure_reason=failure_reason,
        created_at=model.created_at,
        started_at=model.started_at,
        finished_at=model.finished_at,
    )


def apply_job_to_model(job: Job, model: PlatformJobModel) -> None:
    model.organization_id = job.organization_id
    model.job_type = job.job_type.value
    model.payload = job.payload
    model.status = job.status.value
    model.idempotency_key = job.idempotency_key
    model.attempt_count = job.attempt_count
    model.max_attempts = job.max_attempts
    model.result = job.result
    model.failure_reason = job.failure_reason.message if job.failure_reason else None
    model.failure_code = job.failure_reason.code if job.failure_reason else None
    model.created_at = job.created_at
    model.started_at = job.started_at
    model.finished_at = job.finished_at


def job_to_model(job: Job) -> PlatformJobModel:
    model = PlatformJobModel(
        id=job.id,
        organization_id=job.organization_id,
        job_type=job.job_type.value,
        payload=job.payload,
        status=job.status.value,
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
    return model
