from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse

from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.authorization.guards import require_permission
from app.modules.identity.api.membership.dependencies import assert_organization_scope
from app.modules.jobs.api.dependencies import (
    get_enqueue_job_use_case,
    get_get_job_use_case,
    get_in_process_job_worker,
)
from app.modules.jobs.api.error_mapping import map_job_error
from app.modules.jobs.api.mappers import (
    enqueue_request_to_command,
    enqueue_result_to_response,
    get_job_command,
    job_result_to_response,
)
from app.modules.jobs.api.schemas import EnqueueJobRequest, EnqueueJobResponse, ErrorResponse, JobResponse
from app.modules.jobs.application.enqueue_job import EnqueueJobUseCase
from app.modules.jobs.application.get_job import GetJobUseCase
from app.modules.jobs.domain.exceptions import JobError

router = APIRouter(tags=["jobs"])


def _handle_job_errors(use_case_call):
    try:
        return use_case_call()
    except JobError as exc:
        raise map_job_error(exc) from exc


@router.post(
    "/organizations/{organization_id}/jobs",
    response_model=EnqueueJobResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def enqueue_organization_job(
    organization_id: UUID,
    body: EnqueueJobRequest,
    background_tasks: BackgroundTasks,
    context: AuthorizationContext = Depends(require_permission("jobs.platform.enqueue")),
    use_case: EnqueueJobUseCase = Depends(get_enqueue_job_use_case),
    worker=Depends(get_in_process_job_worker),
) -> JSONResponse:
    assert_organization_scope(organization_id, context)
    result = _handle_job_errors(
        lambda: use_case.execute(enqueue_request_to_command(organization_id, body))
    )
    if result.created or result.job.status == "pending":
        background_tasks.add_task(worker.process_batch)
    response = enqueue_result_to_response(result)
    status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_job_status(
    job_id: UUID,
    context: AuthorizationContext = Depends(require_permission("jobs.platform.read")),
    use_case: GetJobUseCase = Depends(get_get_job_use_case),
) -> JobResponse:
    result = _handle_job_errors(
        lambda: use_case.execute(get_job_command(job_id, context.organization_id))
    )
    return job_result_to_response(result)
