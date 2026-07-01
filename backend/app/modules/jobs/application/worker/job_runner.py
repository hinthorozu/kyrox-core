from datetime import UTC, datetime

from app.modules.jobs.domain.entities import Job
from app.modules.jobs.domain.ports import JobHandlerRegistry, JobHandlerResult
from app.modules.jobs.domain.value_objects.failure_reason import FailureReason
from app.modules.jobs.domain.value_objects.job_status import JobStatus


class JobRunner:
    def __init__(self, handler_registry: JobHandlerRegistry) -> None:
        self._handler_registry = handler_registry

    def run(self, job: Job) -> Job:
        handler = self._handler_registry.get(job.job_type)
        if handler is None:
            return _mark_terminal_failure(
                job,
                FailureReason.create(
                    f"No handler registered for job type: {job.job_type.value}",
                    code="handler_not_found",
                ),
            )

        try:
            handler_result = handler.handle(job)
        except Exception as exc:
            return _apply_failure(
                job,
                FailureReason.create(str(exc), code="handler_error"),
                retryable=True,
            )

        if not isinstance(handler_result, JobHandlerResult):
            return _mark_terminal_failure(
                job,
                FailureReason.create("Handler returned invalid result", code="handler_error"),
            )

        if handler_result.retryable is False:
            return _mark_terminal_failure(
                job,
                FailureReason.create("Handler reported non-retryable failure", code="handler_error"),
            )

        return _mark_completed(job, handler_result.result)


def _mark_completed(job: Job, result) -> Job:
    now = datetime.now(UTC)
    if not job.status.can_transition_to(JobStatus.COMPLETED):
        return job
    job.status = JobStatus.COMPLETED
    job.result = result if result is not None else {}
    job.failure_reason = None
    job.finished_at = now
    return job


def _apply_failure(job: Job, reason: FailureReason, *, retryable: bool) -> Job:
    if not retryable or job.attempt_count >= job.max_attempts:
        return _mark_terminal_failure(job, reason)
    if not job.status.can_transition_to(JobStatus.PENDING):
        return job
    job.status = JobStatus.PENDING
    job.failure_reason = reason
    job.started_at = None
    return job


def _mark_terminal_failure(job: Job, reason: FailureReason) -> Job:
    now = datetime.now(UTC)
    if not job.status.can_transition_to(JobStatus.FAILED):
        return job
    job.status = JobStatus.FAILED
    job.failure_reason = reason
    job.finished_at = now
    return job
