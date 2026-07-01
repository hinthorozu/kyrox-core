from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.domain.value_objects.notification_channel import NotificationChannel
from app.modules.notifications.domain.value_objects.recipient import Recipient


class NotificationRepository(Protocol):
    def get_by_id(self, notification_id: UUID) -> Notification | None: ...

    def find_by_idempotency(
        self,
        organization_id: UUID,
        idempotency_key: str,
    ) -> Notification | None: ...

    def save(self, notification: Notification) -> Notification: ...


@dataclass(frozen=True, slots=True)
class OrganizationNotificationSettings:
    email_enabled: bool
    email_from: str | None


class NotificationSettingsReader(Protocol):
    def get_for_organization(self, organization_id: UUID) -> OrganizationNotificationSettings: ...


@dataclass(frozen=True, slots=True)
class ChannelDispatchRequest:
    notification_id: UUID
    organization_id: UUID
    channel: NotificationChannel
    recipient: Recipient
    subject: str
    body: str
    from_address: str | None
    template_key: str | None


@dataclass(frozen=True, slots=True)
class ChannelDispatchResult:
    provider_message_id: str | None = None


class NotificationChannelAdapter(Protocol):
    def send(self, request: ChannelDispatchRequest) -> ChannelDispatchResult: ...


class NotificationChannelRegistry(Protocol):
    def get(self, channel: NotificationChannel) -> NotificationChannelAdapter | None: ...
