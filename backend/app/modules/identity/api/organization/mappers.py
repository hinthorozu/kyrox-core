from app.modules.identity.api.organization.schemas import (
    CreateOrganizationRequest,
    CreateOrganizationResponse,
    OrganizationResponse,
    UpdateOrganizationRequest,
)
from app.modules.identity.application.organization.commands import (
    CreateOrganizationCommand,
    GetOrganizationCommand,
    SuspendOrganizationCommand,
    UpdateOrganizationCommand,
)
from app.modules.identity.application.organization.results import (
    CreateOrganizationResult,
    OrganizationResult,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


def create_organization_request_to_command(
    payload: CreateOrganizationRequest,
    owner_user_id: UserId,
) -> CreateOrganizationCommand:
    return CreateOrganizationCommand(
        owner_user_id=owner_user_id,
        name=payload.name,
        slug=payload.slug,
    )


def get_organization_command(organization_id: OrganizationId) -> GetOrganizationCommand:
    return GetOrganizationCommand(organization_id=organization_id)


def update_organization_request_to_command(
    organization_id: OrganizationId,
    payload: UpdateOrganizationRequest,
) -> UpdateOrganizationCommand:
    return UpdateOrganizationCommand(
        organization_id=organization_id,
        name=payload.name,
    )


def suspend_organization_command(organization_id: OrganizationId) -> SuspendOrganizationCommand:
    return SuspendOrganizationCommand(organization_id=organization_id)


def organization_result_to_response(result: OrganizationResult) -> OrganizationResponse:
    return OrganizationResponse(
        id=result.organization_id.value,
        name=result.name,
        slug=result.slug,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def create_organization_result_to_response(
    result: CreateOrganizationResult,
) -> CreateOrganizationResponse:
    return CreateOrganizationResponse(
        organization=organization_result_to_response(result.organization),
        membership_id=result.membership_id.value,
    )
