from app.modules.identity.application.organization.commands import UpdateOrganizationCommand
from app.modules.identity.application.organization.mappers import to_organization_result
from app.modules.identity.application.organization.policy import OrganizationNamingPolicy
from app.modules.identity.application.organization.results import OrganizationResult
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.organization.exceptions import OrganizationNotFoundError
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository


class UpdateOrganizationUseCase:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        clock: Clock,
        naming_policy: OrganizationNamingPolicy | None = None,
    ) -> None:
        self._organization_repository = organization_repository
        self._clock = clock
        self._naming_policy = naming_policy or OrganizationNamingPolicy()

    def execute(self, command: UpdateOrganizationCommand) -> OrganizationResult:
        organization = self._organization_repository.get_by_id(command.organization_id)
        if organization is None:
            raise OrganizationNotFoundError(
                f"Organization not found: {command.organization_id.value}"
            )

        organization.assert_can_operate()
        if command.name is not None:
            organization.name = self._naming_policy.normalize_name(command.name)
        organization.updated_at = self._clock.now()
        organization = self._organization_repository.update(organization)
        return to_organization_result(organization)
