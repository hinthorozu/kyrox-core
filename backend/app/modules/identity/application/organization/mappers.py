from app.modules.identity.application.organization.results import OrganizationResult
from app.modules.identity.domain.organization.entities.organization import Organization


def to_organization_result(organization: Organization) -> OrganizationResult:
    return OrganizationResult(
        organization_id=organization.id,
        name=organization.name.value,
        slug=organization.slug.value,
        status=organization.status,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
    )
