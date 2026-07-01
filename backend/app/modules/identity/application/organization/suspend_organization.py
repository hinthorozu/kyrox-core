from app.modules.identity.application.organization.commands import SuspendOrganizationCommand
from app.modules.identity.application.organization.mappers import to_organization_result
from app.modules.identity.application.organization.results import OrganizationResult
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.organization.exceptions import OrganizationNotFoundError
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository


class SuspendOrganizationUseCase:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        clock: Clock,
    ) -> None:
        self._organization_repository = organization_repository
        self._clock = clock

    def execute(self, command: SuspendOrganizationCommand) -> OrganizationResult:
        organization = self._organization_repository.get_by_id(command.organization_id)
        if organization is None:
            raise OrganizationNotFoundError(
                f"Organization not found: {command.organization_id.value}"
            )

        organization.suspend(self._clock.now())
        organization = self._organization_repository.update(organization)
        return to_organization_result(organization)
