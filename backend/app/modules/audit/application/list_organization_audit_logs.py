from app.modules.audit.application.query_commands import ListOrganizationAuditLogsCommand
from app.modules.audit.application.query_policy import AuditLogQueryPolicy
from app.modules.audit.application.query_results import AuditLogListResult, AuditLogResult
from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.domain.query.audit_log_query_repository import AuditLogQueryRepository


class ListOrganizationAuditLogsUseCase:
    def __init__(
        self,
        query_repository: AuditLogQueryRepository,
        query_policy: AuditLogQueryPolicy | None = None,
    ) -> None:
        self._query_repository = query_repository
        self._query_policy = query_policy or AuditLogQueryPolicy()

    def execute(self, command: ListOrganizationAuditLogsCommand) -> AuditLogListResult:
        limit = self._query_policy.normalize_limit(command.limit)
        query_filter = self._query_policy.validate_filter(command.query_filter)
        cursor = self._query_policy.decode_cursor(command.cursor)

        page = self._query_repository.list_by_organization(
            command.organization_id,
            query_filter=query_filter,
            cursor=cursor,
            limit=limit,
        )

        next_cursor = (
            self._query_policy.encode_cursor(page.next_cursor)
            if page.next_cursor is not None
            else None
        )
        return AuditLogListResult(
            items=[_to_audit_log_result(item) for item in page.items],
            next_cursor=next_cursor,
        )


def _to_audit_log_result(audit_log: AuditLog) -> AuditLogResult:
    return AuditLogResult(
        id=audit_log.id,
        organization_id=audit_log.organization_id,
        user_id=audit_log.user_id,
        session_id=audit_log.session_id,
        action=audit_log.action,
        resource_type=audit_log.resource_type,
        resource_id=audit_log.resource_id,
        old_values=audit_log.old_values,
        new_values=audit_log.new_values,
        metadata=audit_log.metadata,
        ip_address=audit_log.ip_address,
        user_agent=audit_log.user_agent,
        created_at=audit_log.created_at,
    )
