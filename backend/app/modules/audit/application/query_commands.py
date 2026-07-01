from dataclasses import dataclass
from uuid import UUID

from app.modules.audit.domain.query.audit_log_query_filter import AuditLogQueryFilter


@dataclass(frozen=True)
class ListOrganizationAuditLogsCommand:
    organization_id: UUID
    query_filter: AuditLogQueryFilter
    limit: int
    cursor: str | None = None
