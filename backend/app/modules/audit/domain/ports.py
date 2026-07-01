from typing import Protocol

from app.modules.audit.domain.entities import AuditLog


class AuditLogRepository(Protocol):
    def append(self, audit_log: AuditLog) -> AuditLog: ...
