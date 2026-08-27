import logging
import smtplib
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.modules.jobs.application.enqueue_job import EnqueueJobUseCase
from app.modules.jobs.application.policy import JobPolicy
from app.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository
from app.modules.notifications.application.commands import SendNotificationCommand
from app.modules.notifications.application.identity_templates import (
    IDENTITY_ACTIVATION_TEMPLATE_KEY,
    IDENTITY_PASSWORD_CHANGED_TEMPLATE_KEY,
    IDENTITY_PASSWORD_RESET_TEMPLATE_KEY,
    build_activation_email,
    build_password_changed_email,
    build_password_reset_email,
)
from app.modules.notifications.application.policy import NotificationPolicy
from app.modules.notifications.application.send_notification import SendNotificationUseCase
from app.modules.notifications.domain.exceptions import NotificationDispatchError
from app.modules.notifications.domain.ports import ChannelDispatchRequest
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus
from app.modules.notifications.domain.value_objects.recipient import Recipient
from app.modules.notifications.infrastructure.channels.smtp_email_adapter import SmtpEmailAdapter
from app.modules.notifications.infrastructure.jobs.job_enqueue_adapter import JobsModuleEnqueueAdapter
from app.modules.notifications.infrastructure.repositories import SqlAlchemyNotificationRepository


def test_platform_notification_queues_without_organization_settings(db_session: Session) -> None:
    settings_reader = MagicMock()
    settings_reader.get_for_organization.side_effect = AssertionError(
        "platform identity mail must not read organization mail settings"
    )
    job_repository = SqlAlchemyJobRepository(db_session)
    use_case = SendNotificationUseCase(
        notification_repository=SqlAlchemyNotificationRepository(db_session),
        settings_reader=settings_reader,
        job_enqueue_port=JobsModuleEnqueueAdapter(
            EnqueueJobUseCase(job_repository, JobPolicy())
        ),
        notification_policy=NotificationPolicy(),
    )
    command = SendNotificationCommand(
        organization_id=None,
        channel="email",
        recipient="identity@example.com",
        subject="Identity security message",
        body="Security message body",
        template_key=IDENTITY_PASSWORD_CHANGED_TEMPLATE_KEY,
        idempotency_key="identity-platform-1",
    )

    first = use_case.execute(command)
    second = use_case.execute(command)

    assert first.status == NotificationStatus.QUEUED
    assert first.organization_id is None
    assert first.job_id is not None
    assert second.notification_id == first.notification_id
    assert second.idempotent_replay is True
    queued_job = job_repository.get_by_id(first.job_id)
    assert queued_job is not None
    assert queued_job.organization_id is None
    settings_reader.get_for_organization.assert_not_called()


def test_identity_templates_have_stable_keys_and_require_action_urls() -> None:
    activation = build_activation_email(action_url="https://example.test/activate?t=abc")
    reset = build_password_reset_email(action_url="https://example.test/reset?t=def")
    changed = build_password_changed_email()

    assert activation.template_key == IDENTITY_ACTIVATION_TEMPLATE_KEY
    assert reset.template_key == IDENTITY_PASSWORD_RESET_TEMPLATE_KEY
    assert changed.template_key == IDENTITY_PASSWORD_CHANGED_TEMPLATE_KEY
    assert "https://example.test/activate?t=abc" in activation.body
    assert "https://example.test/reset?t=def" in reset.body
    with pytest.raises(ValueError):
        build_activation_email(action_url="")
    with pytest.raises(ValueError):
        build_password_reset_email(action_url="https://example.test/reset\nInjected: value")


def test_smtp_adapter_dispatches_without_logging_body_or_credentials(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sent_messages = []

    class FakeSmtp:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            assert host == "smtp.example.test"
            assert port == 587
            assert timeout == 4.0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def starttls(self) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            assert username == "core-user"
            assert password == "smtp-password-secret"

        def send_message(self, message):
            sent_messages.append(message)
            return {}

    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    adapter = SmtpEmailAdapter(
        host="smtp.example.test",
        port=587,
        default_from_address="identity@example.test",
        username="core-user",
        password="smtp-password-secret",
        starttls=True,
        timeout_seconds=4.0,
    )
    secret_action = "https://example.test/reset?token=raw-action-token-secret"
    request = ChannelDispatchRequest(
        notification_id=uuid.uuid4(),
        organization_id=None,
        channel=NotificationChannel.EMAIL,
        recipient=Recipient.create("person@example.com"),
        subject="Reset password",
        body=secret_action,
        from_address=None,
        template_key=IDENTITY_PASSWORD_RESET_TEMPLATE_KEY,
    )

    with caplog.at_level(logging.INFO):
        adapter.send(request)

    assert len(sent_messages) == 1
    assert secret_action in sent_messages[0].get_content()
    assert "raw-action-token-secret" not in caplog.text
    assert "smtp-password-secret" not in caplog.text
    assert "person@example.com" not in caplog.text


def test_smtp_adapter_returns_redacted_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingSmtp:
        def __init__(self, *args, **kwargs) -> None:
            raise smtplib.SMTPException("provider-response-with-sensitive-material")

    monkeypatch.setattr(smtplib, "SMTP", FailingSmtp)
    adapter = SmtpEmailAdapter(
        host="smtp.example.test",
        port=587,
        default_from_address="identity@example.test",
        starttls=True,
    )
    request = ChannelDispatchRequest(
        notification_id=uuid.uuid4(),
        organization_id=None,
        channel=NotificationChannel.EMAIL,
        recipient=Recipient.create("person@example.com"),
        subject="Reset password",
        body="raw-action-token-secret",
        from_address=None,
        template_key=IDENTITY_PASSWORD_RESET_TEMPLATE_KEY,
    )

    with pytest.raises(NotificationDispatchError) as exc_info:
        adapter.send(request)

    assert str(exc_info.value) == "Core email provider dispatch failed"
    assert "sensitive-material" not in str(exc_info.value)
