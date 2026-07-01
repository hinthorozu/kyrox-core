from uuid import UUID

from app.modules.audit.api.schemas import (
    AuditLogListQueryParams,
    AuditLogListResponse,
    AuditLogResponse,
)
from app.modules.audit.application.query_commands import ListOrganizationAuditLogsCommand
from app.modules.audit.application.query_results import AuditLogListResult
from app.modules.audit.domain.query.audit_log_query_filter import AuditLogQueryFilter


def audit_log_list_params_to_command(
    organization_id: UUID,
    params: AuditLogListQueryParams,
) -> ListOrganizationAuditLogsCommand:
    return ListOrganizationAuditLogsCommand(
        organization_id=organization_id,
        query_filter=AuditLogQueryFilter(
            action=params.action,
            action_prefix=params.action_prefix,
            resource_type=params.resource_type,
            resource_id=params.resource_id,
            user_id=params.user_id,
            session_id=params.session_id,
            created_from=params.from_,
            created_to=params.to,
        ),
        limit=params.limit,
        cursor=params.cursor,
    )


def audit_log_list_result_to_response(result: AuditLogListResult) -> AuditLogListResponse:
    return AuditLogListResponse(
        items=[
            AuditLogResponse(
                id=item.id,
                organization_id=item.organization_id,
                user_id=item.user_id,
                session_id=item.session_id,
                action=item.action,
                resource_type=item.resource_type,
                resource_id=item.resource_id,
                old_values=item.old_values,
                new_values=item.new_values,
                metadata=item.metadata,
                ip_address=item.ip_address,
                user_agent=item.user_agent,
                created_at=item.created_at,
            )
            for item in result.items
        ],
        next_cursor=result.next_cursor,
    )
