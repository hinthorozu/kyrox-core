from enum import StrEnum


class NotificationStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    SUPPRESSED = "suppressed"

    def is_terminal(self) -> bool:
        return self in {
            NotificationStatus.SENT,
            NotificationStatus.FAILED,
            NotificationStatus.SUPPRESSED,
        }

    def can_transition_to(self, next_status: "NotificationStatus") -> bool:
        allowed: dict[NotificationStatus, frozenset[NotificationStatus]] = {
            NotificationStatus.PENDING: frozenset(
                {NotificationStatus.QUEUED, NotificationStatus.SUPPRESSED}
            ),
            NotificationStatus.QUEUED: frozenset(
                {NotificationStatus.SENDING, NotificationStatus.FAILED, NotificationStatus.SUPPRESSED}
            ),
            NotificationStatus.SENDING: frozenset(
                {NotificationStatus.SENT, NotificationStatus.FAILED, NotificationStatus.SUPPRESSED}
            ),
            NotificationStatus.SENT: frozenset(),
            NotificationStatus.FAILED: frozenset(),
            NotificationStatus.SUPPRESSED: frozenset(),
        }
        return next_status in allowed[self]
