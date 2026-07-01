import logging
from uuid import uuid4

import pytest

from app.modules.notifications.domain.exceptions import NotificationDispatchError
from app.modules.notifications.domain.ports import ChannelDispatchRequest
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.recipient import Recipient
from app.modules.notifications.infrastructure.channels.email_log_stub_adapter import (
    EmailLogStubAdapter,
    redact_recipient,
)


def test_redact_recipient_masks_local_part() -> None:
    assert redact_recipient("user@example.com") == "u***@example.com"


def test_email_stub_logs_without_pii(caplog) -> None:
    adapter = EmailLogStubAdapter()
    recipient = "secret.user@example.com"
    subject = "Private subject"
    body = "Private body content"
    request = ChannelDispatchRequest(
        notification_id=uuid4(),
        organization_id=uuid4(),
        channel=NotificationChannel.EMAIL,
        recipient=Recipient.create(recipient),
        subject=subject,
        body=body,
        from_address=None,
        template_key="welcome",
    )

    with caplog.at_level(logging.INFO):
        adapter.send(request)

    assert len(caplog.records) == 1
    message = caplog.records[0].message
    assert recipient not in message
    assert subject not in message
    assert body not in message
    assert caplog.records[0].recipient_redacted == "s***@example.com"
    assert caplog.records[0].subject_length == len(subject)
    assert caplog.records[0].body_length == len(body)


def test_email_stub_fail_next_raises() -> None:
    adapter = EmailLogStubAdapter(fail_next=True)
    request = ChannelDispatchRequest(
        notification_id=uuid4(),
        organization_id=uuid4(),
        channel=NotificationChannel.EMAIL,
        recipient=Recipient.create("user@example.com"),
        subject="Hello",
        body="Body",
        from_address=None,
        template_key=None,
    )
    with pytest.raises(NotificationDispatchError):
        adapter.send(request)
