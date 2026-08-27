from dataclasses import dataclass
from typing import Protocol

from app.modules.notifications.domain.entities import Notification


@dataclass(frozen=True, slots=True)
class RenderedNotificationContent:
    subject: str
    body: str


class NotificationContentRenderer(Protocol):
    def render(self, notification: Notification) -> RenderedNotificationContent: ...
