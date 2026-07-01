from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.modules.audit.api.dependencies import get_list_organization_audit_logs_use_case
from app.modules.audit.api.error_mapping import map_audit_query_error
from app.modules.audit.api.mappers import (
    audit_log_list_params_to_command,
    audit_log_list_result_to_response,
)
from app.modules.audit.api.schemas import AuditLogListQueryParams, AuditLogListResponse, ErrorResponse
from app.modules.audit.application.list_organization_audit_logs import ListOrganizationAuditLogsUseCase
from app.modules.audit.domain.query_exceptions import InvalidAuditQueryError
from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.authorization.guards import require_permission
from app.modules.identity.api.membership.dependencies import assert_organization_scope

router = APIRouter(tags=["audit"])


def get_audit_log_list_query_params(
    action: str | None = None,
    action_prefix: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    user_id: UUID | None = None,
    session_id: UUID | None = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> AuditLogListQueryParams:
    return AuditLogListQueryParams(
        action=action,
        action_prefix=action_prefix,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        session_id=session_id,
        from_=from_,
        to=to,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/organizations/{organization_id}/audit-logs",
    response_model=AuditLogListResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def list_organization_audit_logs(
    organization_id: UUID,
    params: AuditLogListQueryParams = Depends(get_audit_log_list_query_params),
    context: AuthorizationContext = Depends(require_permission("audit.logs.read")),
    use_case: ListOrganizationAuditLogsUseCase = Depends(get_list_organization_audit_logs_use_case),
) -> AuditLogListResponse:
    assert_organization_scope(organization_id, context)
    try:
        result = use_case.execute(audit_log_list_params_to_command(organization_id, params))
    except InvalidAuditQueryError as exc:
        raise map_audit_query_error(exc) from exc

    return audit_log_list_result_to_response(result)
