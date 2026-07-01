from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuditLogQueryFilter:
    action: str | None = None
    action_prefix: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    user_id: UUID | None = None
    session_id: UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
