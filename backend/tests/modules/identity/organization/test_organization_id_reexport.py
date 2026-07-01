from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId as AuthorizationOrganizationId,
)
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId as CanonicalOrganizationId,
)


def test_authorization_organization_id_reexports_canonical_type() -> None:
    assert AuthorizationOrganizationId is CanonicalOrganizationId
