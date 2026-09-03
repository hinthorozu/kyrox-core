from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.modules.audit.api.dependencies import get_record_organization_audit_event_use_case
from app.modules.audit.application.record_organization_audit_event import (
    RecordOrganizationAuditEventCommand,
    RecordOrganizationAuditEventUseCase,
)
from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.authorization.dependencies import get_platform_user_reader
from app.modules.identity.api.authorization.guards import (
    get_access_token_claims,
    is_super_admin,
    require_permission,
    require_super_admin,
)
from app.modules.identity.api.authorization.scope import assert_organization_scope
from app.modules.identity.api.organization.dependencies import (
    get_create_organization_use_case,
    get_delete_organization_use_case,
    get_get_organization_use_case,
    get_list_organizations_use_case,
    get_reactivate_organization_use_case,
    get_suspend_organization_use_case,
    get_update_organization_use_case,
)
from app.modules.identity.api.organization.error_mapping import (
    map_create_organization_error,
    map_organization_error,
)
from app.modules.identity.api.organization.mappers import (
    create_organization_request_to_command,
    create_organization_result_to_response,
    delete_organization_command,
    get_organization_command,
    list_organizations_command,
    organization_result_to_response,
    organization_results_to_response,
    reactivate_organization_command,
    suspend_organization_command,
    update_organization_request_to_command,
)
from app.modules.identity.api.organization.schemas import (
    CreateOrganizationRequest,
    CreateOrganizationResponse,
    ErrorResponse,
    OrganizationResponse,
    UpdateOrganizationRequest,
)
from app.modules.identity.application.organization.create_organization import CreateOrganizationUseCase
from app.modules.identity.application.organization.delete_organization import DeleteOrganizationUseCase
from app.modules.identity.application.organization.get_organization import GetOrganizationUseCase
from app.modules.identity.application.organization.list_organizations import ListOrganizationsUseCase
from app.modules.identity.application.organization.reactivate_organization import ReactivateOrganizationUseCase
from app.modules.identity.application.organization.suspend_organization import SuspendOrganizationUseCase
from app.modules.identity.application.organization.update_organization import UpdateOrganizationUseCase
from app.modules.identity.domain.authentication.value_objects.security.access_token import AccessTokenClaims
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.ports.platform_user_reader import PlatformUserReader
from app.modules.identity.domain.organization.exceptions import OrganizationError
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _record_lifecycle_audit(
    *,
    organization_id: UUID,
    context: AuthorizationContext,
    claims: AccessTokenClaims,
    action: str,
    new_values: dict[str, object],
    audit_use_case: RecordOrganizationAuditEventUseCase,
) -> None:
    audit_use_case.execute(
        RecordOrganizationAuditEventCommand(
            organization_id=organization_id,
            user_id=context.user_id,
            session_id=claims.sid.value,
            action=action,
            resource_type="organization",
            resource_id=str(organization_id),
            new_values=new_values,
            metadata={"authority": "system"},
        )
    )


@router.post(
    "",
    response_model=CreateOrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def create_organization(
    payload: CreateOrganizationRequest,
    claims: AccessTokenClaims = Depends(require_super_admin),
    use_case: CreateOrganizationUseCase = Depends(get_create_organization_use_case),
) -> CreateOrganizationResponse:
    # Platform organization creation is Super Admin only and does not depend
    # on any permission row or organization membership.
    try:
        result = use_case.execute(
            create_organization_request_to_command(payload, UserId(claims.sub.value))
        )
    except Exception as exc:
        raise map_create_organization_error(exc) from exc

    return create_organization_result_to_response(result)


@router.get(
    "",
    response_model=list[OrganizationResponse],
    responses={401: {"model": ErrorResponse}},
)
def list_organizations(
    claims: AccessTokenClaims = Depends(get_access_token_claims),
    platform_user_reader: PlatformUserReader = Depends(get_platform_user_reader),
    use_case: ListOrganizationsUseCase = Depends(get_list_organizations_use_case),
) -> list[OrganizationResponse]:
    # Super Admin sees every non-deleted organization. Other users see only
    # organizations where they have an effective membership.
    results = use_case.execute(
        list_organizations_command(
            UserId(claims.sub.value),
            include_all=is_super_admin(claims.sub.value, platform_user_reader),
        )
    )
    return organization_results_to_response(results)


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def get_organization(
    organization_id: UUID,
    context: AuthorizationContext = Depends(require_permission("identity.organizations.read")),
    use_case: GetOrganizationUseCase = Depends(get_get_organization_use_case),
) -> OrganizationResponse:
    assert_organization_scope(organization_id, context)
    try:
        result = use_case.execute(get_organization_command(OrganizationId(organization_id)))
    except OrganizationError as exc:
        raise map_organization_error(exc) from exc

    return organization_result_to_response(result)


@router.patch(
    "/{organization_id}",
    response_model=OrganizationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def update_organization(
    organization_id: UUID,
    payload: UpdateOrganizationRequest,
    context: AuthorizationContext = Depends(require_permission("identity.organizations.update")),
    use_case: UpdateOrganizationUseCase = Depends(get_update_organization_use_case),
) -> OrganizationResponse:
    assert_organization_scope(organization_id, context)
    try:
        result = use_case.execute(
            update_organization_request_to_command(OrganizationId(organization_id), payload)
        )
    except OrganizationError as exc:
        raise map_organization_error(exc) from exc

    return organization_result_to_response(result)


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def delete_organization(
    organization_id: UUID,
    context: AuthorizationContext = Depends(require_permission("identity.organizations.delete")),
    claims: AccessTokenClaims = Depends(get_access_token_claims),
    use_case: DeleteOrganizationUseCase = Depends(get_delete_organization_use_case),
    audit_use_case: RecordOrganizationAuditEventUseCase = Depends(
        get_record_organization_audit_event_use_case
    ),
) -> Response:
    assert_organization_scope(organization_id, context)
    try:
        use_case.execute(delete_organization_command(OrganizationId(organization_id)))
        _record_lifecycle_audit(
            organization_id=organization_id,
            context=context,
            claims=claims,
            action="identity.organization.deleted",
            new_values={"deleted": True},
            audit_use_case=audit_use_case,
        )
    except OrganizationError as exc:
        raise map_organization_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{organization_id}/suspend",
    response_model=OrganizationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def suspend_organization(
    organization_id: UUID,
    context: AuthorizationContext = Depends(require_permission("identity.organizations.suspend")),
    claims: AccessTokenClaims = Depends(get_access_token_claims),
    use_case: SuspendOrganizationUseCase = Depends(get_suspend_organization_use_case),
    audit_use_case: RecordOrganizationAuditEventUseCase = Depends(
        get_record_organization_audit_event_use_case
    ),
) -> OrganizationResponse:
    assert_organization_scope(organization_id, context)
    try:
        result = use_case.execute(suspend_organization_command(OrganizationId(organization_id)))
        _record_lifecycle_audit(
            organization_id=organization_id,
            context=context,
            claims=claims,
            action="identity.organization.suspended",
            new_values={"status": result.status.value},
            audit_use_case=audit_use_case,
        )
    except OrganizationError as exc:
        raise map_organization_error(exc) from exc

    return organization_result_to_response(result)


@router.post(
    "/{organization_id}/reactivate",
    response_model=OrganizationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def reactivate_organization(
    organization_id: UUID,
    context: AuthorizationContext = Depends(require_permission("identity.organizations.reactivate")),
    claims: AccessTokenClaims = Depends(get_access_token_claims),
    use_case: ReactivateOrganizationUseCase = Depends(get_reactivate_organization_use_case),
    audit_use_case: RecordOrganizationAuditEventUseCase = Depends(
        get_record_organization_audit_event_use_case
    ),
) -> OrganizationResponse:
    assert_organization_scope(organization_id, context)
    try:
        result = use_case.execute(reactivate_organization_command(OrganizationId(organization_id)))
        _record_lifecycle_audit(
            organization_id=organization_id,
            context=context,
            claims=claims,
            action="identity.organization.reactivated",
            new_values={"status": result.status.value},
            audit_use_case=audit_use_case,
        )
    except OrganizationError as exc:
        raise map_organization_error(exc) from exc

    return organization_result_to_response(result)
