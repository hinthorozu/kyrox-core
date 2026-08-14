from app.modules.identity.domain.organization.exceptions import OrganizationNotFoundError
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


class RemoveOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository) -> None:
        self._organization_repository = organization_repository

    def execute(self, organization_id: OrganizationId) -> None:
        if self._organization_repository.get_by_id(organization_id) is None:
            raise OrganizationNotFoundError(f"Organization not found: {organization_id.value}")
        self._organization_repository.remove(organization_id)
