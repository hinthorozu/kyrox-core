class JobError(Exception):
    """Base exception for jobs domain errors."""


class JobNotFoundError(JobError):
    """Raised when a job does not exist or is not visible in org scope."""


class JobAccessDeniedError(JobError):
    """Raised when a job belongs to another organization."""


class InvalidJobTypeError(JobError):
    """Raised when job_type violates format rules."""


class InvalidJobPayloadError(JobError):
    """Raised when payload or related JSON input is invalid."""


class InvalidJobTransitionError(JobError):
    """Raised when a status transition is not allowed."""


class DuplicateIdempotencyConflictError(JobError):
    """Raised when idempotency key is reused with a different payload."""


class JobHandlerNotFoundError(JobError):
    """Raised when no handler is registered for a job type."""


class JobAlreadyTerminalError(JobError):
    """Raised when a terminal job is processed again."""
