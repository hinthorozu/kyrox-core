from uuid import UUID

from app.modules.jobs.application.commands import EnqueueJobCommand, GetJobCommand
from app.modules.jobs.application.results import EnqueueJobResult, JobResult
from app.modules.jobs.api.schemas import EnqueueJobRequest, EnqueueJobResponse, JobResponse


def enqueue_request_to_command(
    organization_id: UUID,
    body: EnqueueJobRequest,
) -> EnqueueJobCommand:
    return EnqueueJobCommand(
        organization_id=organization_id,
        job_type=body.job_type,
        payload=body.payload,
        idempotency_key=body.idempotency_key,
        max_attempts=body.max_attempts,
    )


def get_job_command(job_id: UUID, organization_id: UUID) -> GetJobCommand:
    return GetJobCommand(job_id=job_id, organization_id=organization_id)


def job_result_to_response(result: JobResult) -> JobResponse:
    return JobResponse(
        id=result.id,
        organization_id=result.organization_id,
        job_type=result.job_type,
        status=result.status,
        payload=result.payload,
        idempotency_key=result.idempotency_key,
        attempt_count=result.attempt_count,
        max_attempts=result.max_attempts,
        result=result.result,
        failure_reason=result.failure_reason,
        failure_code=result.failure_code,
        created_at=result.created_at,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )


def enqueue_result_to_response(result: EnqueueJobResult) -> EnqueueJobResponse:
    return EnqueueJobResponse(
        job=job_result_to_response(result.job),
        created=result.created,
    )
