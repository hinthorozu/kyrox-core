from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.domain.value_objects.failure_reason import FailureReason
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus
from app.modules.notifications.domain.value_objects.recipient import Recipient
from app.modules.notifications.infrastructure.persistence.models import PlatformNotificationModel


def notification_to_domain(model: PlatformNotificationModel) -> Notification:
    failure_reason = None
    if model.failure_reason is not None:
        failure_reason = FailureReason.create(model.failure_reason, code=model.failure_code)
    return Notification(
        id=model.id,
        organization_id=model.organization_id,
        channel=NotificationChannel(model.channel),
        recipient=Recipient(value=model.recipient),
        subject=model.subject,
        body=model.body,
        template_key=model.template_key,
        variables=model.variables,
        status=NotificationStatus(model.status),
        idempotency_key=model.idempotency_key,
        job_id=model.job_id,
        failure_reason=failure_reason,
        created_at=model.created_at,
        queued_at=model.queued_at,
        sent_at=model.sent_at,
        failed_at=model.failed_at,
        suppressed_at=model.suppressed_at,
    )


def notification_to_model(notification: Notification) -> PlatformNotificationModel:
    failure_reason = None
    failure_code = None
    if notification.failure_reason is not None:
        failure_reason = notification.failure_reason.message
        failure_code = notification.failure_reason.code
    return PlatformNotificationModel(
        id=notification.id,
        organization_id=notification.organization_id,
        channel=notification.channel.value,
        recipient=notification.recipient.value,
        subject=notification.subject,
        body=notification.body,
        template_key=notification.template_key,
        variables=notification.variables,
        status=notification.status.value,
        idempotency_key=notification.idempotency_key,
        job_id=notification.job_id,
        failure_reason=failure_reason,
        failure_code=failure_code,
        created_at=notification.created_at,
        queued_at=notification.queued_at,
        sent_at=notification.sent_at,
        failed_at=notification.failed_at,
        suppressed_at=notification.suppressed_at,
    )


def apply_notification_to_model(
    notification: Notification,
    model: PlatformNotificationModel,
) -> None:
    model.organization_id = notification.organization_id
    model.channel = notification.channel.value
    model.recipient = notification.recipient.value
    model.subject = notification.subject
    model.body = notification.body
    model.template_key = notification.template_key
    model.variables = notification.variables
    model.status = notification.status.value
    model.idempotency_key = notification.idempotency_key
    model.job_id = notification.job_id
    if notification.failure_reason is not None:
        model.failure_reason = notification.failure_reason.message
        model.failure_code = notification.failure_reason.code
    else:
        model.failure_reason = None
        model.failure_code = None
    model.queued_at = notification.queued_at
    model.sent_at = notification.sent_at
    model.failed_at = notification.failed_at
    model.suppressed_at = notification.suppressed_at
