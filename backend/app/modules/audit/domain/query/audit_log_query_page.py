from dataclasses import dataclass

from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.domain.query.audit_log_cursor import AuditLogCursor


@dataclass(frozen=True)
class AuditLogQueryPage:
    items: list[AuditLog]
    next_cursor: AuditLogCursor | None
