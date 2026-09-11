from typing import Protocol
from uuid import UUID

from app.modules.audit.domain.entities import AuditLog


class AuditLogRepository(Protocol):
    def append(self, audit_log: AuditLog) -> AuditLog: ...

    def purge_for_organization(self, organization_id: UUID) -> int: ...
