from typing import Protocol
from uuid import UUID

from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.domain.retention_policy import AuditRetentionMinimizationCounts


class AuditLogRepository(Protocol):
    def append(self, audit_log: AuditLog) -> AuditLog: ...

    def count_for_organization(self, organization_id: UUID) -> int: ...

    def minimize_for_terminal_retention(
        self,
        organization_id: UUID,
    ) -> AuditRetentionMinimizationCounts: ...

    def purge_for_organization(self, organization_id: UUID) -> int: ...
