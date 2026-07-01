from uuid import UUID

from app.modules.notifications.api.schemas import (
    NotificationResponse,
    SendNotificationRequest,
    SendNotificationResponse,
)
from app.modules.notifications.application.commands import GetNotificationCommand, SendNotificationCommand
from app.modules.notifications.application.results import GetNotificationResult, SendNotificationResult


def send_request_to_command(
    organization_id: UUID,
    body: SendNotificationRequest,
) -> SendNotificationCommand:
    return SendNotificationCommand(
        organization_id=organization_id,
        channel=body.channel,
        recipient=body.recipient,
        subject=body.subject,
        body=body.body,
        template_key=body.template_key,
        variables=body.variables,
        idempotency_key=body.idempotency_key,
    )


def get_notification_command(
    notification_id: UUID,
    organization_id: UUID,
) -> GetNotificationCommand:
    return GetNotificationCommand(
        notification_id=notification_id,
        organization_id=organization_id,
    )


def send_result_to_response(result: SendNotificationResult) -> SendNotificationResponse:
    return SendNotificationResponse(
        notification=_send_result_to_notification_response(result),
        created=not result.idempotent_replay,
    )


def get_result_to_response(result: GetNotificationResult) -> NotificationResponse:
    return NotificationResponse(
        id=result.notification_id,
        organization_id=result.organization_id,
        channel=result.channel.value,
        recipient=result.recipient,
        subject=result.subject,
        status=result.status.value,
        template_key=result.template_key,
        job_id=result.job_id,
        failure_reason=result.failure_reason,
        failure_code=result.failure_code,
        created_at=result.created_at,
        queued_at=result.queued_at,
        sent_at=result.sent_at,
        failed_at=result.failed_at,
        suppressed_at=result.suppressed_at,
    )


def _send_result_to_notification_response(result: SendNotificationResult) -> NotificationResponse:
    return NotificationResponse(
        id=result.notification_id,
        organization_id=result.organization_id,
        channel=result.channel.value,
        recipient=result.recipient,
        subject=result.subject,
        status=result.status.value,
        template_key=result.template_key,
        job_id=result.job_id,
        failure_reason=result.failure_reason,
        failure_code=result.failure_code,
        created_at=result.created_at,
        queued_at=result.queued_at,
        sent_at=result.sent_at,
        failed_at=result.failed_at,
        suppressed_at=result.suppressed_at,
    )
