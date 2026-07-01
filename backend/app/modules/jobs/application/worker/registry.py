from app.modules.jobs.domain.ports import JobHandler, JobHandlerRegistry
from app.modules.jobs.domain.value_objects.job_type import JobType


class InMemoryJobHandlerRegistry(JobHandlerRegistry):
    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_type: JobType, handler: JobHandler) -> None:
        self._handlers[job_type.value] = handler

    def get(self, job_type: JobType) -> JobHandler | None:
        return self._handlers.get(job_type.value)
