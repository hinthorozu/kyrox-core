from app.modules.identity.application.organization.commands import ListOrganizationsCommand
from app.modules.identity.application.organization.mappers import to_organization_result
from app.modules.identity.application.organization.results import OrganizationResult
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository
from app.modules.identity.domain.organization.ports.user_organization_reader import UserOrganizationReader


class ListOrganizationsUseCase:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        user_organization_reader: UserOrganizationReader,
    ) -> None:
        self._organization_repository = organization_repository
        self._user_organization_reader = user_organization_reader

    def execute(self, command: ListOrganizationsCommand) -> list[OrganizationResult]:
        if command.include_all:
            return [
                to_organization_result(organization)
                for organization in self._organization_repository.list_all()
            ]

        organization_id = self._user_organization_reader.get_organization_id(command.user_id)
        if organization_id is None:
            return []

        organization = self._organization_repository.get_by_id(organization_id)
        if organization is None:
            return []

        return [to_organization_result(organization)]
