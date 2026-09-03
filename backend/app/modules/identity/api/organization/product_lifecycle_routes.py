from secrets import compare_digest
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.modules.identity.api.organization.dependencies import get_organization_repository
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId

router = APIRouter(prefix="/organizations", tags=["organizations"])


class ProductOrganizationLifecycleSnapshot(BaseModel):
    organization_id: UUID
    status: OrganizationStatus
    work_allowed: bool


def _require_product_lifecycle_token(
    token: str | None = Header(default=None, alias="X-Kyrox-Product-Lifecycle-Token"),
) -> None:
    expected = settings.CORE_PRODUCT_LIFECYCLE_TOKEN
    if token is None or not compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid product lifecycle credential",
        )


@router.get(
    "/{organization_id}/lifecycle-snapshot",
    response_model=ProductOrganizationLifecycleSnapshot,
    responses={
        401: {"description": "Invalid product lifecycle credential"},
        404: {"description": "Organization not found"},
    },
    dependencies=[Depends(_require_product_lifecycle_token)],
)
def get_product_organization_lifecycle_snapshot(
    organization_id: UUID,
    repository: OrganizationRepository = Depends(get_organization_repository),
) -> ProductOrganizationLifecycleSnapshot:
    organization = repository.get_by_id(OrganizationId(organization_id))
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return ProductOrganizationLifecycleSnapshot(
        organization_id=organization_id,
        status=organization.status,
        work_allowed=organization.status is OrganizationStatus.ACTIVE,
    )
