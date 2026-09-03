from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


def organization_allows_authentication(
    user: User,
    organization_repository: OrganizationRepository,
) -> bool:
    if user.is_super_admin:
        return True
    if user.organization_id is None:
        return False

    organization = organization_repository.get_by_id(OrganizationId(user.organization_id))
    return organization is not None and organization.is_active()
