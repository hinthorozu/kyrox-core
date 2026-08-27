from collections.abc import Callable

from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.identity.application.authentication.identity_action_tokens import (
    MaterializeIdentityActionToken,
)
from app.modules.identity.infrastructure.authentication.clock import UtcClock
from app.modules.identity.infrastructure.authentication.repositories.sqlalchemy_identity_action_token_repository import (
    SqlAlchemyIdentityActionTokenRepository,
)
from app.modules.identity.infrastructure.authentication.security.identity_action_token_service import (
    IdentityActionTokenService,
)
from app.modules.jobs.application.worker.registry import InMemoryJobHandlerRegistry
from app.modules.jobs.domain.value_objects.job_type import JobType
from app.modules.notifications.application.identity_delivery_renderer import (
    IdentityNotificationContentRenderer,
)
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.infrastructure.channels.email_log_stub_adapter import EmailLogStubAdapter
from app.modules.notifications.infrastructure.channels.registry import InMemoryNotificationChannelRegistry
from app.modules.notifications.infrastructure.channels.smtp_email_adapter import SmtpEmailAdapter
from app.modules.notifications.infrastructure.jobs.job_enqueue_adapter import NOTIFICATION_DISPATCH_JOB_TYPE
from app.modules.notifications.infrastructure.jobs.notification_dispatch_job_handler import (
    NotificationDispatchJobHandler,
)


def build_notification_channel_registry() -> InMemoryNotificationChannelRegistry:
    registry = InMemoryNotificationChannelRegistry()
    provider = settings.CORE_EMAIL_PROVIDER.strip().lower()
    if provider == "log":
        adapter = EmailLogStubAdapter()
    elif provider == "smtp":
        if settings.CORE_SMTP_HOST is None or settings.CORE_EMAIL_FROM is None:
            raise RuntimeError(
                "CORE_SMTP_HOST and CORE_EMAIL_FROM are required when CORE_EMAIL_PROVIDER=smtp"
            )
        adapter = SmtpEmailAdapter(
            host=settings.CORE_SMTP_HOST,
            port=settings.CORE_SMTP_PORT,
            default_from_address=settings.CORE_EMAIL_FROM,
            username=settings.CORE_SMTP_USERNAME,
            password=settings.CORE_SMTP_PASSWORD,
            starttls=settings.CORE_SMTP_STARTTLS,
            use_ssl=settings.CORE_SMTP_SSL,
            timeout_seconds=settings.CORE_SMTP_TIMEOUT_SECONDS,
        )
    else:
        raise RuntimeError(f"Unsupported CORE_EMAIL_PROVIDER: {provider}")
    registry.register(NotificationChannel.EMAIL, adapter)
    return registry


def build_identity_notification_content_renderer(
    session: DbSession,
) -> IdentityNotificationContentRenderer:
    token_service = IdentityActionTokenService(
        settings.CORE_IDENTITY_ACTION_TOKEN_SECRET_KEY
    )
    materializer = MaterializeIdentityActionToken(
        repository=SqlAlchemyIdentityActionTokenRepository(session),
        token_service=token_service,
        clock=UtcClock(),
    )
    return IdentityNotificationContentRenderer(
        materialize_identity_action_token=materializer,
        activation_url_template=settings.CORE_IDENTITY_ACTIVATION_URL_TEMPLATE,
        password_reset_url_template=settings.CORE_IDENTITY_PASSWORD_RESET_URL_TEMPLATE,
    )


def build_notification_dispatch_job_handler(
    session_factory: Callable[[], DbSession],
    channel_registry: InMemoryNotificationChannelRegistry,
) -> NotificationDispatchJobHandler:
    return NotificationDispatchJobHandler(
        session_factory=session_factory,
        channel_registry=channel_registry,
        content_renderer_factory=build_identity_notification_content_renderer,
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
