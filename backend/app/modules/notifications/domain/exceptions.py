class NotificationError(Exception):
    """Base exception for notifications domain errors."""


class NotificationNotFoundError(NotificationError):
    """Raised when a notification does not exist or is not visible in org scope."""


class InvalidNotificationRequestError(NotificationError):
    """Raised when a notification request violates validation rules."""


class DuplicateIdempotencyConflictError(NotificationError):
    """Raised when idempotency key is reused with a different payload."""


class InvalidNotificationTransitionError(NotificationError):
    """Raised when a status transition is not allowed."""


class UnsupportedNotificationChannelError(NotificationError):
    """Raised when the requested channel is not supported."""


class NotificationDispatchError(NotificationError):
    """Raised when channel dispatch fails."""
