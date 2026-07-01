import uuid

import pytest

from app.modules.identity.domain.organization.exceptions import InvalidOrganizationSlugError
from app.modules.identity.domain.organization.value_objects import (
    OrganizationId,
    OrganizationName,
    OrganizationSlug,
)


def test_organization_name_create() -> None:
    name = OrganizationName.create("  Acme Corp  ")
    assert name.value == "Acme Corp"


def test_organization_slug_create() -> None:
    slug = OrganizationSlug.create("Acme-Corp")
    assert slug.value == "acme-corp"


def test_organization_slug_rejects_invalid_value() -> None:
    with pytest.raises(InvalidOrganizationSlugError):
        OrganizationSlug.create("ab")


def test_organization_id_requires_uuid() -> None:
    with pytest.raises(TypeError):
        OrganizationId("not-a-uuid")  # type: ignore[arg-type]

    assert OrganizationId(uuid.uuid4()).value
