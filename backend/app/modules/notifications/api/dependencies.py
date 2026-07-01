from dataclasses import dataclass

from fastapi import BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.db.session import get_db
from app.modules.jobs.api.dependencies import get_enqueue_job_use_case, get_in_process_job_worker
from app.modules.jobs.application.enqueue_job import EnqueueJobUseCase
from app.modules.notifications.application.dispatch_notification import DispatchNotificationUseCase
from app.modules.notifications.application.get_notification import GetNotificationUseCase
from app.modules.notifications.application.policy import NotificationPolicy
from app.modules.notifications.application.send_notification import SendNotificationUseCase
from app.modules.notifications.domain.ports import NotificationChannelRegistry, NotificationRepository
from app.modules.notifications.domain.ports import NotificationSettingsReader
from app.modules.notifications.application.ports.job_enqueue_port import JobEnqueuePort
from app.modules.notifications.infrastructure.jobs.handler_context import (
    reset_notification_handler_session,
    set_notification_handler_session,
)
from app.modules.notifications.infrastructure.jobs.job_enqueue_adapter import JobsModuleEnqueueAdapter
from app.modules.notifications.infrastructure.repositories import SqlAlchemyNotificationRepository
from app.modules.notifications.infrastructure.settings_reader import (
    NotificationSettingsReaderAdapter,
    SettingRepositoryOrganizationSettingReader,
)
from app.modules.settings.infrastructure.repositories import SqlAlchemySettingRepository


def schedule_notification_worker(
    background_tasks: BackgroundTasks,
    worker,
    db: DbSession,
) -> None:
    def _run_worker() -> None:
        token = set_notification_handler_session(db)
        try:
            worker.process_batch()
        finally:
            reset_notification_handler_session(token)

    background_tasks.add_task(_run_worker)


@dataclass(frozen=True, slots=True)
class NotificationWorkerScheduler:
    worker: object
    db: DbSession

    def schedule(self, background_tasks: BackgroundTasks) -> None:
        schedule_notification_worker(background_tasks, self.worker, self.db)


def get_notification_worker_scheduler(
    worker=Depends(get_in_process_job_worker),
    db: DbSession = Depends(get_db),
) -> NotificationWorkerScheduler:
    return NotificationWorkerScheduler(worker=worker, db=db)


def get_notification_repository(db: DbSession = Depends(get_db)) -> NotificationRepository:
    return SqlAlchemyNotificationRepository(db)


def get_notification_policy() -> NotificationPolicy:
    return NotificationPolicy()


def get_notification_settings_reader(db: DbSession = Depends(get_db)) -> NotificationSettingsReader:
    setting_reader = SettingRepositoryOrganizationSettingReader(SqlAlchemySettingRepository(db))
    return NotificationSettingsReaderAdapter(setting_reader)


def get_job_enqueue_port(
    enqueue_job_use_case: EnqueueJobUseCase = Depends(get_enqueue_job_use_case),
) -> JobEnqueuePort:
    return JobsModuleEnqueueAdapter(enqueue_job_use_case)


def get_send_notification_use_case(
    notification_repository: NotificationRepository = Depends(get_notification_repository),
    settings_reader: NotificationSettingsReader = Depends(get_notification_settings_reader),
    job_enqueue_port: JobEnqueuePort = Depends(get_job_enqueue_port),
    notification_policy: NotificationPolicy = Depends(get_notification_policy),
) -> SendNotificationUseCase:
    return SendNotificationUseCase(
        notification_repository=notification_repository,
        settings_reader=settings_reader,
        job_enqueue_port=job_enqueue_port,
        notification_policy=notification_policy,
    )


def get_get_notification_use_case(
    notification_repository: NotificationRepository = Depends(get_notification_repository),
) -> GetNotificationUseCase:
    return GetNotificationUseCase(notification_repository=notification_repository)


def get_notification_channel_registry(request: Request) -> NotificationChannelRegistry:
    return request.app.state.notification_channel_registry


def get_dispatch_notification_use_case(
    notification_repository: NotificationRepository = Depends(get_notification_repository),
    channel_registry: NotificationChannelRegistry = Depends(get_notification_channel_registry),
    settings_reader: NotificationSettingsReader = Depends(get_notification_settings_reader),
    notification_policy: NotificationPolicy = Depends(get_notification_policy),
) -> DispatchNotificationUseCase:
    return DispatchNotificationUseCase(
        notification_repository=notification_repository,
        channel_registry=channel_registry,
        settings_reader=settings_reader,
        notification_policy=notification_policy,
    )
