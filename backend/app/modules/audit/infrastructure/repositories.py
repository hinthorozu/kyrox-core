from sqlalchemy.orm import Session as DbSession

from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.infrastructure.persistence.mappers import (
    audit_log_to_domain,
    audit_log_to_model,
)
from app.modules.audit.infrastructure.persistence.models import AuditLogModel


class SqlAlchemyAuditLogRepository:
    """Append-only audit log persistence."""

    def __init__(self, session: DbSession) -> None:
        self._session = session

    def append(self, audit_log: AuditLog) -> AuditLog:
        model = audit_log_to_model(audit_log)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return audit_log_to_domain(model)
