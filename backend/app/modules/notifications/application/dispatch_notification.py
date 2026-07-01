from datetime import UTC, datetime

from app.modules.notifications.application.commands import DispatchNotificationCommand
from app.modules.notifications.application.policy import NotificationPolicy
from app.modules.notifications.application.results import DispatchNotificationResult
from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.domain.exceptions import (
    InvalidNotificationTransitionError,
    NotificationDispatchError,
    NotificationNotFoundError,
)
from app.modules.notifications.domain.ports import (
    ChannelDispatchRequest,
    NotificationChannelRegistry,
    NotificationRepository,
    NotificationSettingsReader,
)
from app.modules.notifications.domain.value_objects.failure_reason import FailureReason
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus


class DispatchNotificationUseCase:
    def __init__(
        self,
        notification_repository: NotificationRepository,
        channel_registry: NotificationChannelRegistry,
        settings_reader: NotificationSettingsReader,
        notification_policy: NotificationPolicy,
    ) -> None:
        self._notification_repository = notification_repository
        self._channel_registry = channel_registry
        self._settings_reader = settings_reader
        self._notification_policy = notification_policy

    def execute(self, command: DispatchNotificationCommand) -> DispatchNotificationResult:
        notification = self._notification_repository.get_by_id(command.notification_id)
        if notification is None:
            raise NotificationNotFoundError("Notification not found")

        if notification.status.is_terminal():
            return DispatchNotificationResult(
                notification_id=notification.id,
                status=notification.status,
                idempotent_noop=True,
            )

        settings = self._settings_reader.get_for_organization(notification.organization_id)
        if notification.channel == NotificationChannel.EMAIL and not settings.email_enabled:
            suppressed = self._transition(
                notification,
                NotificationStatus.SUPPRESSED,
                suppressed_at=datetime.now(UTC),
            )
            saved = self._notification_repository.save(suppressed)
            return DispatchNotificationResult(
                notification_id=saved.id,
                status=saved.status,
                idempotent_noop=False,
            )

        sending = self._transition(notification, NotificationStatus.SENDING)
        self._notification_repository.save(sending)

        adapter = self._channel_registry.get(notification.channel)
        if adapter is None:
            failed = self._transition(
                sending,
                NotificationStatus.FAILED,
                failure_reason=FailureReason.create(
                    f"No adapter registered for channel {notification.channel.value}",
                    code="unsupported_channel",
                ),
                failed_at=datetime.now(UTC),
            )
            saved = self._notification_repository.save(failed)
            return DispatchNotificationResult(
                notification_id=saved.id,
                status=saved.status,
                idempotent_noop=False,
            )

        request = ChannelDispatchRequest(
            notification_id=notification.id,
            organization_id=notification.organization_id,
            channel=notification.channel,
            recipient=notification.recipient,
            subject=notification.subject,
            body=notification.body,
            from_address=settings.email_from,
            template_key=notification.template_key,
        )

        try:
            adapter.send(request)
        except NotificationDispatchError as exc:
            failed = self._transition(
                sending,
                NotificationStatus.FAILED,
                failure_reason=FailureReason.create(str(exc), code="dispatch_failed"),
                failed_at=datetime.now(UTC),
            )
            saved = self._notification_repository.save(failed)
            return DispatchNotificationResult(
                notification_id=saved.id,
                status=saved.status,
                idempotent_noop=False,
            )
        except Exception as exc:
            failed = self._transition(
                sending,
                NotificationStatus.FAILED,
                failure_reason=FailureReason.create(str(exc), code="dispatch_error"),
                failed_at=datetime.now(UTC),
            )
            saved = self._notification_repository.save(failed)
            return DispatchNotificationResult(
                notification_id=saved.id,
                status=saved.status,
                idempotent_noop=False,
            )

        sent = self._transition(
            sending,
            NotificationStatus.SENT,
            sent_at=datetime.now(UTC),
        )
        saved = self._notification_repository.save(sent)
        return DispatchNotificationResult(
            notification_id=saved.id,
            status=saved.status,
            idempotent_noop=False,
        )

    @staticmethod
    def _transition(
        notification: Notification,
        next_status: NotificationStatus,
        *,
        failure_reason: FailureReason | None = None,
        queued_at: datetime | None = None,
        sent_at: datetime | None = None,
        failed_at: datetime | None = None,
        suppressed_at: datetime | None = None,
    ) -> Notification:
        if not notification.status.can_transition_to(next_status):
            raise InvalidNotificationTransitionError(
                f"Cannot transition notification from {notification.status.value} to {next_status.value}"
            )
        return Notification(
            id=notification.id,
            organization_id=notification.organization_id,
            channel=notification.channel,
            recipient=notification.recipient,
            subject=notification.subject,
            body=notification.body,
            template_key=notification.template_key,
            variables=notification.variables,
            status=next_status,
            idempotency_key=notification.idempotency_key,
            job_id=notification.job_id,
            failure_reason=failure_reason if failure_reason is not None else notification.failure_reason,
            created_at=notification.created_at,
            queued_at=queued_at if queued_at is not None else notification.queued_at,
            sent_at=sent_at if sent_at is not None else notification.sent_at,
            failed_at=failed_at if failed_at is not None else notification.failed_at,
            suppressed_at=suppressed_at if suppressed_at is not None else notification.suppressed_at,
        )
