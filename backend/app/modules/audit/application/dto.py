from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class RecordAuditEventCommand:
    action: str
    resource_type: str
    organization_id: UUID | None = None
    user_id: UUID | None = None
    session_id: UUID | None = None
    resource_id: str | None = None
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
