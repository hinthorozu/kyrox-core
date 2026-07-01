from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.notifications.application.commands import SendNotificationCommand
from app.modules.notifications.application.policy import NotificationPolicy
from app.modules.notifications.application.ports.job_enqueue_port import JobEnqueuePort
from app.modules.notifications.application.results import SendNotificationResult
from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.domain.exceptions import DuplicateIdempotencyConflictError
from app.modules.notifications.domain.ports import NotificationRepository, NotificationSettingsReader
from app.modules.notifications.domain.value_objects.failure_reason import FailureReason
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus


class SendNotificationUseCase:
    def __init__(
        self,
        notification_repository: NotificationRepository,
        settings_reader: NotificationSettingsReader,
        job_enqueue_port: JobEnqueuePort,
        notification_policy: NotificationPolicy,
    ) -> None:
        self._notification_repository = notification_repository
        self._settings_reader = settings_reader
        self._job_enqueue_port = job_enqueue_port
        self._notification_policy = notification_policy

    def execute(self, command: SendNotificationCommand) -> SendNotificationResult:
        channel = self._notification_policy.normalize_channel(command.channel)
        recipient = self._notification_policy.normalize_recipient(command.recipient, channel)
        subject = self._notification_policy.normalize_subject(command.subject)
        body = self._notification_policy.normalize_body(command.body)
        template_key = self._notification_policy.normalize_template_key(command.template_key)
        variables = self._notification_policy.normalize_variables(command.variables)
        idempotency_key = self._notification_policy.normalize_idempotency_key(command.idempotency_key)

        if idempotency_key is not None:
            existing = self._notification_repository.find_by_idempotency(
                command.organization_id,
                idempotency_key,
            )
            if existing is not None:
                if not self._notification_policy.payloads_match(
                    channel=channel,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    template_key=template_key,
                    existing_channel=existing.channel,
                    existing_recipient=existing.recipient,
                    existing_subject=existing.subject,
                    existing_body=existing.body,
                    existing_template_key=existing.template_key,
                ):
                    raise DuplicateIdempotencyConflictError(
                        "Idempotency key already used with a different payload"
                    )
                return self._to_result(existing, idempotent_replay=True)

        settings = self._settings_reader.get_for_organization(command.organization_id)
        now = datetime.now(UTC)
        notification_id = uuid4()

        if channel.value == "email" and not settings.email_enabled:
            suppressed = Notification(
                id=notification_id,
                organization_id=command.organization_id,
                channel=channel,
                recipient=recipient,
                subject=subject,
                body=body,
                template_key=template_key,
                variables=variables,
                status=NotificationStatus.SUPPRESSED,
                idempotency_key=idempotency_key,
                job_id=None,
                failure_reason=None,
                created_at=now,
                queued_at=None,
                sent_at=None,
                failed_at=None,
                suppressed_at=now,
            )
            saved = self._notification_repository.save(suppressed)
            return self._to_result(saved, idempotent_replay=False)

        pending = Notification(
            id=notification_id,
            organization_id=command.organization_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            template_key=template_key,
            variables=variables,
            status=NotificationStatus.PENDING,
            idempotency_key=idempotency_key,
            job_id=None,
            failure_reason=None,
            created_at=now,
            queued_at=None,
            sent_at=None,
            failed_at=None,
            suppressed_at=None,
        )
        saved = self._notification_repository.save(pending)

        try:
            job_id = self._job_enqueue_port.enqueue_notification_dispatch(
                organization_id=command.organization_id,
                notification_id=saved.id,
            )
        except Exception as exc:
            failed = self._copy_notification(
                saved,
                status=NotificationStatus.FAILED,
                failure_reason=FailureReason.create(str(exc), code="enqueue_failed"),
                failed_at=datetime.now(UTC),
            )
            saved = self._notification_repository.save(failed)
            return self._to_result(saved, idempotent_replay=False)

        queued = self._copy_notification(
            saved,
            status=NotificationStatus.QUEUED,
            job_id=job_id,
            queued_at=datetime.now(UTC),
        )
        saved = self._notification_repository.save(queued)
        return self._to_result(saved, idempotent_replay=False)

    @staticmethod
    def _to_result(notification: Notification, *, idempotent_replay: bool) -> SendNotificationResult:
        failure_reason = None
        failure_code = None
        if notification.failure_reason is not None:
            failure_reason = notification.failure_reason.message
            failure_code = notification.failure_reason.code
        return SendNotificationResult(
            notification_id=notification.id,
            organization_id=notification.organization_id,
            channel=notification.channel,
            recipient=notification.recipient.value,
            subject=notification.subject,
            template_key=notification.template_key,
            status=notification.status,
            job_id=notification.job_id,
            failure_reason=failure_reason,
            failure_code=failure_code,
            idempotent_replay=idempotent_replay,
            created_at=notification.created_at,
            queued_at=notification.queued_at,
            sent_at=notification.sent_at,
            failed_at=notification.failed_at,
            suppressed_at=notification.suppressed_at,
        )

    @staticmethod
    def _copy_notification(
        notification: Notification,
        *,
        status: NotificationStatus | None = None,
        job_id: UUID | None = None,
        failure_reason: FailureReason | None = None,
        queued_at: datetime | None = None,
        failed_at: datetime | None = None,
    ) -> Notification:
        return Notification(
            id=notification.id,
            organization_id=notification.organization_id,
            channel=notification.channel,
            recipient=notification.recipient,
            subject=notification.subject,
            body=notification.body,
            template_key=notification.template_key,
            variables=notification.variables,
            status=status if status is not None else notification.status,
            idempotency_key=notification.idempotency_key,
            job_id=job_id if job_id is not None else notification.job_id,
            failure_reason=failure_reason if failure_reason is not None else notification.failure_reason,
            created_at=notification.created_at,
            queued_at=queued_at if queued_at is not None else notification.queued_at,
            sent_at=notification.sent_at,
            failed_at=failed_at if failed_at is not None else notification.failed_at,
            suppressed_at=notification.suppressed_at,
        )
