from fastapi import HTTPException, status

from app.modules.notifications.domain.exceptions import (
    DuplicateIdempotencyConflictError,
    InvalidNotificationRequestError,
    InvalidNotificationTransitionError,
    NotificationError,
    NotificationNotFoundError,
    UnsupportedNotificationChannelError,
)


def map_notification_error(exc: NotificationError) -> HTTPException:
    if isinstance(exc, NotificationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, DuplicateIdempotencyConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, (InvalidNotificationRequestError, UnsupportedNotificationChannelError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, InvalidNotificationTransitionError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
