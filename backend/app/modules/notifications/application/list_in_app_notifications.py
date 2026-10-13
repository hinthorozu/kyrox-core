from uuid import UUID

from app.modules.notifications.domain.entities import Notification
from app.modules.notifications.domain.ports import NotificationRepository


class ListSystemInAppNotificationsUseCase:
    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    def execute(self, user_id: UUID, *, limit: int = 50) -> list[Notification]:
        return self._repository.list_system_in_app(user_id, limit=limit)
