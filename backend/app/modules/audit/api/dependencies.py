from fastapi import Depends
from sqlalchemy.orm import Session as DbSession

from app.db.session import get_db
from app.modules.audit.application.list_organization_audit_logs import ListOrganizationAuditLogsUseCase
from app.modules.audit.domain.query.audit_log_query_repository import AuditLogQueryRepository
from app.modules.audit.infrastructure.query_repository import SqlAlchemyAuditLogQueryRepository


def get_audit_log_query_repository(
    db: DbSession = Depends(get_db),
) -> AuditLogQueryRepository:
    return SqlAlchemyAuditLogQueryRepository(db)


def get_list_organization_audit_logs_use_case(
    query_repository: AuditLogQueryRepository = Depends(get_audit_log_query_repository),
) -> ListOrganizationAuditLogsUseCase:
    return ListOrganizationAuditLogsUseCase(query_repository=query_repository)
