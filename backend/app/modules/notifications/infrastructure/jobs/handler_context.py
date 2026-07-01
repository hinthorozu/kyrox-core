from contextvars import ContextVar

from sqlalchemy.orm import Session as DbSession

_notification_handler_session: ContextVar[DbSession | None] = ContextVar(
    "notification_handler_session",
    default=None,
)


def set_notification_handler_session(session: DbSession):
    return _notification_handler_session.set(session)


def reset_notification_handler_session(token) -> None:
    _notification_handler_session.reset(token)


def get_notification_handler_session() -> DbSession | None:
    return _notification_handler_session.get()
