import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.modules.jobs.application.enqueue_job import EnqueueJobUseCase
from app.modules.jobs.application.policy import JobPolicy
from app.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository
from app.modules.notifications.application.commands import (
    DispatchNotificationCommand,
    GetNotificationCommand,
    SendNotificationCommand,
)
from app.modules.notifications.application.dispatch_notification import DispatchNotificationUseCase
from app.modules.notifications.application.get_notification import GetNotificationUseCase
from app.modules.notifications.application.policy import NotificationPolicy
from app.modules.notifications.application.send_notification import SendNotificationUseCase
from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.domain.exceptions import DuplicateIdempotencyConflictError
from app.modules.notifications.domain.ports import OrganizationNotificationSettings
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus
from app.modules.notifications.domain.value_objects.recipient import Recipient
from app.modules.notifications.infrastructure.channels.registry import InMemoryNotificationChannelRegistry
from app.modules.notifications.infrastructure.channels.email_log_stub_adapter import EmailLogStubAdapter
from app.modules.notifications.infrastructure.jobs.job_enqueue_adapter import JobsModuleEnqueueAdapter
from app.modules.notifications.infrastructure.repositories import SqlAlchemyNotificationRepository


def _build_send_use_case(db_session: Session) -> SendNotificationUseCase:
    settings_reader = MagicMock()
    settings_reader.get_for_organization.return_value = OrganizationNotificationSettings(
        email_enabled=True,
        email_from=None,
    )
    return SendNotificationUseCase(
        notification_repository=SqlAlchemyNotificationRepository(db_session),
        settings_reader=settings_reader,
        job_enqueue_port=JobsModuleEnqueueAdapter(
            EnqueueJobUseCase(SqlAlchemyJobRepository(db_session), JobPolicy())
        ),
        notification_policy=NotificationPolicy(),
    )


def test_send_notification_queues_job(db_session: Session) -> None:
    org_id = uuid.uuid4()
    use_case = _build_send_use_case(db_session)
    result = use_case.execute(
        SendNotificationCommand(
            organization_id=org_id,
            channel="email",
            recipient="user@example.com",
            subject="Hello",
            body="World",
        )
    )
    assert result.status == NotificationStatus.QUEUED
    assert result.job_id is not None


def test_send_notification_suppressed_when_email_disabled(db_session: Session) -> None:
    org_id = uuid.uuid4()
    settings_reader = MagicMock()
    settings_reader.get_for_organization.return_value = OrganizationNotificationSettings(
        email_enabled=False,
        email_from=None,
    )
    use_case = SendNotificationUseCase(
        notification_repository=SqlAlchemyNotificationRepository(db_session),
        settings_reader=settings_reader,
        job_enqueue_port=MagicMock(),
        notification_policy=NotificationPolicy(),
    )
    result = use_case.execute(
        SendNotificationCommand(
            organization_id=org_id,
            channel="email",
            recipient="user@example.com",
            subject="Hello",
            body="World",
        )
    )
    assert result.status == NotificationStatus.SUPPRESSED
    assert result.job_id is None


def test_send_notification_idempotency_replay(db_session: Session) -> None:
    org_id = uuid.uuid4()
    use_case = _build_send_use_case(db_session)
    command = SendNotificationCommand(
        organization_id=org_id,
        channel="email",
        recipient="user@example.com",
        subject="Hello",
        body="World",
        idempotency_key="send-1",
    )
    first = use_case.execute(command)
    second = use_case.execute(command)
    assert first.notification_id == second.notification_id
    assert second.idempotent_replay is True


def test_send_notification_idempotency_conflict(db_session: Session) -> None:
    org_id = uuid.uuid4()
    use_case = _build_send_use_case(db_session)
    use_case.execute(
        SendNotificationCommand(
            organization_id=org_id,
            channel="email",
            recipient="user@example.com",
            subject="Hello",
            body="World",
            idempotency_key="send-1",
        )
    )
    with pytest.raises(DuplicateIdempotencyConflictError):
        use_case.execute(
            SendNotificationCommand(
                organization_id=org_id,
                channel="email",
                recipient="other@example.com",
                subject="Hello",
                body="World",
                idempotency_key="send-1",
            )
        )


def test_dispatch_is_idempotent_for_terminal_status(db_session: Session) -> None:
    org_id = uuid.uuid4()
    notification_id = uuid.uuid4()
    now = datetime.now(UTC)
    repository = SqlAlchemyNotificationRepository(db_session)
    repository.save(
        Notification(
            id=notification_id,
            organization_id=org_id,
            channel=NotificationChannel.EMAIL,
            recipient=Recipient.create("user@example.com"),
            subject="Hello",
            body="World",
            template_key=None,
            variables=None,
            status=NotificationStatus.SENT,
            idempotency_key=None,
            job_id=uuid.uuid4(),
            failure_reason=None,
            created_at=now,
            queued_at=now,
            sent_at=now,
            failed_at=None,
            suppressed_at=None,
        )
    )
    registry = InMemoryNotificationChannelRegistry()
    failing_adapter = EmailLogStubAdapter(fail_next=True)
    registry.register(NotificationChannel.EMAIL, failing_adapter)
    settings_reader = MagicMock()
    settings_reader.get_for_organization.return_value = OrganizationNotificationSettings(
        email_enabled=True,
        email_from=None,
    )
    use_case = DispatchNotificationUseCase(
        notification_repository=repository,
        channel_registry=registry,
        settings_reader=settings_reader,
        notification_policy=NotificationPolicy(),
    )
    result = use_case.execute(DispatchNotificationCommand(notification_id=notification_id))
    assert result.idempotent_noop is True
    assert result.status == NotificationStatus.SENT


def test_get_notification_masks_other_organization(db_session: Session) -> None:
    org_id = uuid.uuid4()
    other_org_id = uuid.uuid4()
    notification_id = uuid.uuid4()
    now = datetime.now(UTC)
    repository = SqlAlchemyNotificationRepository(db_session)
    repository.save(
        Notification(
            id=notification_id,
            organization_id=other_org_id,
            channel=NotificationChannel.EMAIL,
            recipient=Recipient.create("user@example.com"),
            subject="Hello",
            body="World",
            template_key=None,
            variables=None,
            status=NotificationStatus.SENT,
            idempotency_key=None,
            job_id=None,
            failure_reason=None,
            created_at=now,
            queued_at=None,
            sent_at=now,
            failed_at=None,
            suppressed_at=None,
        )
    )
    use_case = GetNotificationUseCase(repository)
    with pytest.raises(Exception):
        use_case.execute(GetNotificationCommand(notification_id=notification_id, organization_id=org_id))
