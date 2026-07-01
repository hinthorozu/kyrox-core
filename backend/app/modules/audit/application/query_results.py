from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AuditLogResult:
    id: UUID
    organization_id: UUID | None
    user_id: UUID | None
    session_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    metadata: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


@dataclass(frozen=True)
class AuditLogListResult:
    items: list[AuditLogResult]
    next_cursor: str | None
