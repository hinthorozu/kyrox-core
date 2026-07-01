from app.modules.identity.application.organization.commands import GetOrganizationCommand
from app.modules.identity.application.organization.mappers import to_organization_result
from app.modules.identity.application.organization.results import OrganizationResult
from app.modules.identity.domain.organization.exceptions import OrganizationNotFoundError
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository


class GetOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository) -> None:
        self._organization_repository = organization_repository

    def execute(self, command: GetOrganizationCommand) -> OrganizationResult:
        organization = self._organization_repository.get_by_id(command.organization_id)
        if organization is None:
            raise OrganizationNotFoundError(
                f"Organization not found: {command.organization_id.value}"
            )
        return to_organization_result(organization)
