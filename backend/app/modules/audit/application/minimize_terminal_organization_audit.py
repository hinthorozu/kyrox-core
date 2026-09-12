from dataclasses import dataclass
from uuid import UUID

from app.modules.audit.domain.ports import AuditLogRepository
from app.modules.audit.domain.retention_policy import (
    AUDIT_RETENTION_POLICY_VERSION,
    AuditRetentionMinimizationCounts,
)


@dataclass(frozen=True, slots=True)
class MinimizeTerminalOrganizationAuditResult:
    organization_id: UUID
    policy_version: str
    counts: AuditRetentionMinimizationCounts


class MinimizeTerminalOrganizationAuditUseCase:
    def __init__(self, audit_log_repository: AuditLogRepository) -> None:
        self._audit_log_repository = audit_log_repository

    def execute(self, organization_id: UUID) -> MinimizeTerminalOrganizationAuditResult:
        counts = self._audit_log_repository.minimize_for_terminal_retention(organization_id)
        return MinimizeTerminalOrganizationAuditResult(
            organization_id=organization_id,
            policy_version=AUDIT_RETENTION_POLICY_VERSION,
            counts=counts,
        )
