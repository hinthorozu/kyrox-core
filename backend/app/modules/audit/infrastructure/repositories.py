from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session as DbSession

from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.infrastructure.persistence.mappers import (
    audit_log_to_domain,
    audit_log_to_model,
)
from app.modules.audit.infrastructure.persistence.models import AuditLogModel


class SqlAlchemyAuditLogRepository:
    """Audit log persistence, including policy-authorized terminal retention purge."""

    def __init__(self, session: DbSession) -> None:
        self._session = session

    def append(self, audit_log: AuditLog) -> AuditLog:
        model = audit_log_to_model(audit_log)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return audit_log_to_domain(model)

    def purge_for_organization(self, organization_id: UUID) -> int:
        result = self._session.execute(
            delete(AuditLogModel).where(AuditLogModel.organization_id == organization_id)
        )
        self._session.flush()
        return int(result.rowcount or 0)
