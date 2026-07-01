import pytest

from app.modules.notifications.application.policy import NotificationPolicy
from app.modules.notifications.domain.exceptions import InvalidNotificationRequestError
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel


def test_normalize_recipient_requires_valid_email() -> None:
    policy = NotificationPolicy()
    with pytest.raises(InvalidNotificationRequestError):
        policy.normalize_recipient("not-an-email", NotificationChannel.EMAIL)


def test_normalize_subject_rejects_empty() -> None:
    policy = NotificationPolicy()
    with pytest.raises(InvalidNotificationRequestError):
        policy.normalize_subject("   ")
