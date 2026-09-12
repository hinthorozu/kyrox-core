from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session as DbSession

from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.domain.retention_policy import (
    FAIR_CLOSURE_ACTION_PREFIX,
    RETAINED_AUDIT_ACTION_PREFIXES,
    AuditRetentionMinimizationCounts,
)
from app.modules.audit.infrastructure.persistence.mappers import (
    audit_log_to_domain,
    audit_log_to_model,
)
from app.modules.audit.infrastructure.persistence.models import AuditLogModel


class SqlAlchemyAuditLogRepository:
    """Audit log persistence, including terminal minimization and retention purge."""

    def __init__(self, session: DbSession) -> None:
        self._session = session

    def append(self, audit_log: AuditLog) -> AuditLog:
        model = audit_log_to_model(audit_log)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return audit_log_to_domain(model)

    def count_for_organization(self, organization_id: UUID) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(AuditLogModel)
                .where(AuditLogModel.organization_id == organization_id)
            )
            or 0
        )

    def minimize_for_terminal_retention(
        self,
        organization_id: UUID,
    ) -> AuditRetentionMinimizationCounts:
        retained_clause = or_(
            *(AuditLogModel.action.startswith(prefix) for prefix in RETAINED_AUDIT_ACTION_PREFIXES)
        )
        deleted = self._session.execute(
            delete(AuditLogModel).where(
                AuditLogModel.organization_id == organization_id,
                ~retained_clause,
            )
        )
        sanitized = self._session.execute(
            update(AuditLogModel)
            .where(
                AuditLogModel.organization_id == organization_id,
                AuditLogModel.action.startswith(FAIR_CLOSURE_ACTION_PREFIX),
            )
            .values(
                old_values=None,
                new_values=None,
                event_metadata=None,
                ip_address=None,
                user_agent=None,
            )
        )
        self._session.flush()
        return AuditRetentionMinimizationCounts(
            deleted_non_retention_rows=int(deleted.rowcount or 0),
            sanitized_retention_rows=int(sanitized.rowcount or 0),
        )

    def purge_for_organization(self, organization_id: UUID) -> int:
        result = self._session.execute(
            delete(AuditLogModel).where(AuditLogModel.organization_id == organization_id)
        )
        self._session.flush()
        return int(result.rowcount or 0)
