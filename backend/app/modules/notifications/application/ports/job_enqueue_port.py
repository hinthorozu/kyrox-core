from typing import Protocol
from uuid import UUID


class JobEnqueuePort(Protocol):
    def enqueue_notification_dispatch(
        self,
        *,
        organization_id: UUID,
        notification_id: UUID,
    ) -> UUID: ...
