from uuid import UUID

from fastapi import APIRouter, Depends

from app.modules.identity.api.authorization.context import AuthenticatedOrganizationContext
from app.modules.identity.api.authorization.dependencies import get_authorization_service
from app.modules.identity.api.authorization.guards import require_organization_membership
from app.modules.identity.api.authorization.mappers import authorization_decision_to_response
from app.modules.identity.api.authorization.schemas import (
    CheckPermissionRequest,
    CheckPermissionResponse,
    ErrorResponse,
)
from app.modules.identity.api.membership.dependencies import assert_organization_scope
from app.modules.identity.api.authorization.error_mapping import map_authorization_error
from app.modules.identity.application.authorization import AuthorizationService, CheckPermissionCommand
from app.modules.identity.domain.authorization.exceptions import InvalidPermissionError
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId

router = APIRouter(tags=["authorization"])


@router.post(
    "/organizations/{organization_id}/authorization/check",
    response_model=CheckPermissionResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def check_organization_permission(
    organization_id: UUID,
    body: CheckPermissionRequest,
    context: AuthenticatedOrganizationContext = Depends(require_organization_membership()),
    authorization_service: AuthorizationService = Depends(get_authorization_service),
) -> CheckPermissionResponse:
    assert_organization_scope(organization_id, context)
    try:
        decision = authorization_service.check_permission(
            CheckPermissionCommand(
                user_id=UserId(context.user_id),
                organization_id=OrganizationId(context.organization_id),
                permission_code=body.permission_code,
            )
        )
    except InvalidPermissionError as exc:
        raise map_authorization_error(exc) from exc
    return authorization_decision_to_response(decision)
