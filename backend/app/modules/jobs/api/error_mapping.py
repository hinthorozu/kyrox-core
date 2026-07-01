from app.core.exceptions import AppException
from app.modules.jobs.domain.exceptions import (
    DuplicateIdempotencyConflictError,
    InvalidJobPayloadError,
    InvalidJobTypeError,
    JobError,
    JobNotFoundError,
)


def map_job_error(exc: JobError) -> AppException:
    if isinstance(exc, JobNotFoundError):
        return AppException(str(exc), status_code=404)
    if isinstance(exc, DuplicateIdempotencyConflictError):
        return AppException(str(exc), status_code=409)
    if isinstance(exc, (InvalidJobTypeError, InvalidJobPayloadError)):
        return AppException(str(exc), status_code=400)
    return AppException(str(exc), status_code=400)
