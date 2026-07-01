from typing import Protocol
from uuid import UUID

from app.modules.audit.domain.query.audit_log_cursor import AuditLogCursor
from app.modules.audit.domain.query.audit_log_query_filter import AuditLogQueryFilter
from app.modules.audit.domain.query.audit_log_query_page import AuditLogQueryPage


class AuditLogQueryRepository(Protocol):
    def list_by_organization(
        self,
        organization_id: UUID,
        *,
        query_filter: AuditLogQueryFilter,
        cursor: AuditLogCursor | None,
        limit: int,
    ) -> AuditLogQueryPage: ...
