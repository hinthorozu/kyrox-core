from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus


def test_terminal_statuses() -> None:
    assert NotificationStatus.SENT.is_terminal()
    assert NotificationStatus.FAILED.is_terminal()
    assert NotificationStatus.SUPPRESSED.is_terminal()
    assert not NotificationStatus.PENDING.is_terminal()
    assert not NotificationStatus.QUEUED.is_terminal()
    assert not NotificationStatus.SENDING.is_terminal()


def test_allowed_transitions() -> None:
    assert NotificationStatus.PENDING.can_transition_to(NotificationStatus.QUEUED)
    assert NotificationStatus.PENDING.can_transition_to(NotificationStatus.SUPPRESSED)
    assert NotificationStatus.QUEUED.can_transition_to(NotificationStatus.SENDING)
    assert NotificationStatus.SENDING.can_transition_to(NotificationStatus.SENT)
    assert NotificationStatus.SENT.can_transition_to(NotificationStatus.QUEUED) is False
