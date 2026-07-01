from app.modules.jobs.domain.entities import Job
from app.modules.jobs.domain.ports import JobHandler, JobHandlerResult


class EchoJobHandler(JobHandler):
    def handle(self, job: Job) -> JobHandlerResult:
        return JobHandlerResult(result={"echo": job.payload})
