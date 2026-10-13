from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.infrastructure.persistence.mappers import (
    apply_notification_to_model,
    notification_to_domain,
    notification_to_model,
)
from app.modules.notifications.infrastructure.persistence.models import PlatformNotificationModel


class SqlAlchemyNotificationRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def list_system_in_app(self, user_id: UUID, *, limit: int) -> list[Notification]:
        models = self._session.scalars(
            select(PlatformNotificationModel)
            .where(
                PlatformNotificationModel.organization_id.is_(None),
                PlatformNotificationModel.channel == "in_app",
                PlatformNotificationModel.status == "sent",
                PlatformNotificationModel.recipient.in_(("super_admin", str(user_id))),
            )
            .order_by(PlatformNotificationModel.created_at.desc(), PlatformNotificationModel.id.desc())
            .limit(limit)
        ).all()
        return [notification_to_domain(model) for model in models]

    def get_by_id(self, notification_id: UUID) -> Notification | None:
        model = self._session.get(PlatformNotificationModel, notification_id)
        if model is None:
            return None
        return notification_to_domain(model)

    def find_by_idempotency(
        self,
        organization_id: UUID | None,
        idempotency_key: str,
    ) -> Notification | None:
        stmt = (
            select(PlatformNotificationModel)
            .where(PlatformNotificationModel.organization_id == organization_id)
            .where(PlatformNotificationModel.idempotency_key == idempotency_key)
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return notification_to_domain(model)

    def save(self, notification: Notification) -> Notification:
        existing = self._session.get(PlatformNotificationModel, notification.id)
        if existing is None:
            model = notification_to_model(notification)
            self._session.add(model)
            self._session.flush()
            return notification_to_domain(model)

        apply_notification_to_model(notification, existing)
        self._session.flush()
        return notification_to_domain(existing)
