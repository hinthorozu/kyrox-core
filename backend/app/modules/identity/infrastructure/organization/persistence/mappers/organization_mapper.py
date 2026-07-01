from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.domain.organization.value_objects.profile.organization_name import (
    OrganizationName,
)
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import (
    OrganizationSlug,
)
from app.modules.identity.infrastructure.organization.persistence.models.organization import (
    OrganizationModel,
)


class OrganizationMapper:
    @staticmethod
    def to_domain(model: OrganizationModel) -> Organization:
        return Organization(
            id=OrganizationId(model.id),
            name=OrganizationName(value=model.name),
            slug=OrganizationSlug(value=model.slug),
            status=OrganizationStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(entity: Organization) -> OrganizationModel:
        return OrganizationModel(
            id=entity.id.value,
            name=entity.name.value,
            slug=entity.slug.value,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    @staticmethod
    def apply_to_model(entity: Organization, model: OrganizationModel) -> None:
        model.name = entity.name.value
        model.slug = entity.slug.value
        model.status = entity.status.value
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at
