from app.modules.notifications.application.commands import GetNotificationCommand
from app.modules.notifications.application.results import GetNotificationResult
from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.domain.exceptions import NotificationNotFoundError
from app.modules.notifications.domain.ports import NotificationRepository


class GetNotificationUseCase:
    def __init__(self, notification_repository: NotificationRepository) -> None:
        self._notification_repository = notification_repository

    def execute(self, command: GetNotificationCommand) -> GetNotificationResult:
        notification = self._notification_repository.get_by_id(command.notification_id)
        if notification is None or notification.organization_id != command.organization_id:
            raise NotificationNotFoundError("Notification not found")
        return self._to_result(notification)

    @staticmethod
    def _to_result(notification: Notification) -> GetNotificationResult:
        failure_reason = None
        failure_code = None
        if notification.failure_reason is not None:
            failure_reason = notification.failure_reason.message
            failure_code = notification.failure_reason.code
        return GetNotificationResult(
            notification_id=notification.id,
            organization_id=notification.organization_id,
            channel=notification.channel,
            recipient=notification.recipient.value,
            subject=notification.subject,
            body=notification.body,
            template_key=notification.template_key,
            variables=notification.variables,
            status=notification.status,
            job_id=notification.job_id,
            failure_reason=failure_reason,
            failure_code=failure_code,
            created_at=notification.created_at,
            queued_at=notification.queued_at,
            sent_at=notification.sent_at,
            failed_at=notification.failed_at,
            suppressed_at=notification.suppressed_at,
        )
