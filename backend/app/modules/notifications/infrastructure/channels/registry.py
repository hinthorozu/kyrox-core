from app.modules.notifications.domain.ports import (
    NotificationChannelAdapter,
    NotificationChannelRegistry,
)
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel


class InMemoryNotificationChannelRegistry(NotificationChannelRegistry):
    def __init__(self) -> None:
        self._adapters: dict[str, NotificationChannelAdapter] = {}

    def register(self, channel: NotificationChannel, adapter: NotificationChannelAdapter) -> None:
        self._adapters[channel.value] = adapter

    def get(self, channel: NotificationChannel) -> NotificationChannelAdapter | None:
        return self._adapters.get(channel.value)
