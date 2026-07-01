from collections.abc import Callable

from sqlalchemy.orm import Session as DbSession

from app.db.session import SessionLocal
from app.modules.jobs.application.worker.registry import InMemoryJobHandlerRegistry
from app.modules.jobs.domain.value_objects.job_type import JobType
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.infrastructure.channels.email_log_stub_adapter import EmailLogStubAdapter
from app.modules.notifications.infrastructure.channels.registry import InMemoryNotificationChannelRegistry
from app.modules.notifications.infrastructure.jobs.job_enqueue_adapter import NOTIFICATION_DISPATCH_JOB_TYPE
from app.modules.notifications.infrastructure.jobs.notification_dispatch_job_handler import (
    NotificationDispatchJobHandler,
)


def build_notification_channel_registry() -> InMemoryNotificationChannelRegistry:
    registry = InMemoryNotificationChannelRegistry()
    registry.register(NotificationChannel.EMAIL, EmailLogStubAdapter())
    return registry


def build_notification_dispatch_job_handler(
    session_factory: Callable[[], DbSession],
    channel_registry: InMemoryNotificationChannelRegistry,
) -> NotificationDispatchJobHandler:
    return NotificationDispatchJobHandler(
        session_factory=session_factory,
        channel_registry=channel_registry,
    )


def register_notification_platform(
    job_handler_registry: InMemoryJobHandlerRegistry,
) -> InMemoryNotificationChannelRegistry:
    channel_registry = build_notification_channel_registry()
    job_handler_registry.register(
        JobType.create(NOTIFICATION_DISPATCH_JOB_TYPE),
        build_notification_dispatch_job_handler(SessionLocal, channel_registry),
    )
    return channel_registry
