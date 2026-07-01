import uuid
from datetime import UTC, datetime

from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.domain.organization.value_objects.profile.organization_name import OrganizationName
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import OrganizationSlug
from app.modules.identity.infrastructure.organization.persistence.mappers.organization_mapper import (
    OrganizationMapper,
)
from app.modules.identity.infrastructure.organization.persistence.models.organization import OrganizationModel


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def test_organization_mapper_roundtrip() -> None:
    organization = Organization(
        id=OrganizationId(uuid.uuid4()),
        name=OrganizationName.create("Acme Corp"),
        slug=OrganizationSlug.create("acme-corp"),
        status=OrganizationStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),
    )

    model = OrganizationMapper.to_model(organization)
    assert isinstance(model, OrganizationModel)
    restored = OrganizationMapper.to_domain(model)
    assert restored.id.value == organization.id.value
    assert restored.slug.value == organization.slug.value
