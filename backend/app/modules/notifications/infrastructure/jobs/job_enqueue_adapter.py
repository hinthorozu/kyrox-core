from uuid import UUID

from app.modules.jobs.application.commands import EnqueueJobCommand
from app.modules.jobs.application.enqueue_job import EnqueueJobUseCase
from app.modules.notifications.application.ports.job_enqueue_port import JobEnqueuePort

NOTIFICATION_DISPATCH_JOB_TYPE = "core.platform.notification.dispatch"
NOTIFICATION_DISPATCH_MAX_ATTEMPTS = 3


class JobsModuleEnqueueAdapter(JobEnqueuePort):
    def __init__(self, enqueue_job_use_case: EnqueueJobUseCase) -> None:
        self._enqueue_job_use_case = enqueue_job_use_case

    def enqueue_notification_dispatch(
        self,
        *,
        organization_id: UUID,
        notification_id: UUID,
    ) -> UUID:
        result = self._enqueue_job_use_case.execute(
            EnqueueJobCommand(
                organization_id=organization_id,
                job_type=NOTIFICATION_DISPATCH_JOB_TYPE,
                payload={"notification_id": str(notification_id)},
                idempotency_key=f"notification-{notification_id}",
                max_attempts=NOTIFICATION_DISPATCH_MAX_ATTEMPTS,
            )
        )
        return result.job.id
