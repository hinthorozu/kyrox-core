from app.modules.identity.application.organization.mappers import to_organization_result
from app.modules.identity.application.organization.results import OrganizationResult
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository


class ListOrganizationsUseCase:
    def __init__(self, organization_repository: OrganizationRepository) -> None:
        self._organization_repository = organization_repository

    def execute(self) -> list[OrganizationResult]:
        return [to_organization_result(item) for item in self._organization_repository.list_all()]
