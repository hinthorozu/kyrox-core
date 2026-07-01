from app.modules.jobs.application.commands import ProcessPendingJobsCommand
from app.modules.jobs.application.policy import JobPolicy
from app.modules.jobs.application.worker.job_runner import JobRunner
from app.modules.jobs.domain.ports import JobHandlerRegistry, JobRepository


class ProcessPendingJobsUseCase:
    def __init__(
        self,
        job_repository: JobRepository,
        handler_registry: JobHandlerRegistry,
        job_policy: JobPolicy | None = None,
    ) -> None:
        self._job_repository = job_repository
        self._handler_registry = handler_registry
        self._job_policy = job_policy or JobPolicy()
        self._job_runner = JobRunner(handler_registry)

    def execute(self, command: ProcessPendingJobsCommand) -> int:
        batch_size = self._job_policy.normalize_batch_size(command.limit)
        claimed_jobs = self._job_repository.claim_next_pending(limit=batch_size)
        processed = 0
        for job in claimed_jobs:
            updated = self._job_runner.run(job)
            self._job_repository.save(updated)
            processed += 1
        return processed
