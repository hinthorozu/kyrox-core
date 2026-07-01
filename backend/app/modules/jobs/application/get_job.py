from app.modules.jobs.application.commands import GetJobCommand
from app.modules.jobs.application.job_result_mapper import to_job_result
from app.modules.jobs.application.results import JobResult
from app.modules.jobs.domain.exceptions import JobNotFoundError
from app.modules.jobs.domain.ports import JobRepository


class GetJobUseCase:
    def __init__(self, job_repository: JobRepository) -> None:
        self._job_repository = job_repository

    def execute(self, command: GetJobCommand) -> JobResult:
        job = self._job_repository.get_by_id(command.job_id)
        if job is None or job.organization_id != command.organization_id:
            raise JobNotFoundError(f"Job not found: {command.job_id}")
        return to_job_result(job)
