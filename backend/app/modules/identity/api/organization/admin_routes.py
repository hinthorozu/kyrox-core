from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.modules.identity.api.authorization.guards import require_super_admin
from app.modules.identity.api.organization.dependencies import (
    get_create_organization_use_case,
    get_get_organization_use_case,
    get_list_organizations_use_case,
    get_remove_organization_use_case,
    get_update_organization_use_case,
)
from app.modules.identity.api.organization.error_mapping import (
    map_create_organization_error,
    map_organization_error,
)
from app.modules.identity.api.organization.mappers import (
    create_organization_request_to_command,
    create_organization_result_to_response,
    get_organization_command,
    organization_result_to_response,
    update_organization_request_to_command,
)
from app.modules.identity.api.organization.schemas import (
    CreateOrganizationRequest,
    CreateOrganizationResponse,
    ErrorResponse,
    OrganizationListResponse,
    OrganizationResponse,
    UpdateOrganizationRequest,
)
from app.modules.identity.application.organization.create_organization import CreateOrganizationUseCase
from app.modules.identity.application.organization.get_organization import GetOrganizationUseCase
from app.modules.identity.application.organization.list_organizations import ListOrganizationsUseCase
from app.modules.identity.application.organization.remove_organization import RemoveOrganizationUseCase
from app.modules.identity.application.organization.update_organization import UpdateOrganizationUseCase
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.access_token import AccessTokenClaims
from app.modules.identity.domain.organization.exceptions import OrganizationError
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId

router = APIRouter(prefix="/admin/organizations", tags=["admin-organizations"])


@router.get(
    "",
    response_model=OrganizationListResponse,
    responses={403: {"model": ErrorResponse}},
)
def list_organizations(
    _claims: AccessTokenClaims = Depends(require_super_admin),
    use_case: ListOrganizationsUseCase = Depends(get_list_organizations_use_case),
) -> OrganizationListResponse:
    return OrganizationListResponse(
        items=[organization_result_to_response(item) for item in use_case.execute()]
    )


@router.post(
    "",
    response_model=CreateOrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_organization(
    payload: CreateOrganizationRequest,
    claims: AccessTokenClaims = Depends(require_super_admin),
    use_case: CreateOrganizationUseCase = Depends(get_create_organization_use_case),
) -> CreateOrganizationResponse:
    try:
        result = use_case.execute(
            create_organization_request_to_command(payload, UserId(claims.sub.value))
        )
    except Exception as exc:
        raise map_create_organization_error(exc) from exc
    return create_organization_result_to_response(result)


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_organization(
    organization_id: UUID,
    _claims: AccessTokenClaims = Depends(require_super_admin),
    use_case: GetOrganizationUseCase = Depends(get_get_organization_use_case),
) -> OrganizationResponse:
    try:
        result = use_case.execute(get_organization_command(OrganizationId(organization_id)))
    except OrganizationError as exc:
        raise map_organization_error(exc) from exc
    return organization_result_to_response(result)


@router.patch(
    "/{organization_id}",
    response_model=OrganizationResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_organization(
    organization_id: UUID,
    payload: UpdateOrganizationRequest,
    _claims: AccessTokenClaims = Depends(require_super_admin),
    use_case: UpdateOrganizationUseCase = Depends(get_update_organization_use_case),
) -> OrganizationResponse:
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
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def delete_organization(
    organization_id: UUID,
    _claims: AccessTokenClaims = Depends(require_super_admin),
    use_case: RemoveOrganizationUseCase = Depends(get_remove_organization_use_case),
) -> Response:
    try:
        use_case.execute(OrganizationId(organization_id))
    except OrganizationError as exc:
        raise map_organization_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
