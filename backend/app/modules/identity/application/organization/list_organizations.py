from app.modules.identity.application.organization.commands import ListOrganizationsCommand
from app.modules.identity.application.organization.mappers import to_organization_result
from app.modules.identity.application.organization.results import OrganizationResult
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository


class ListOrganizationsUseCase:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        membership_repository: MembershipRepository,
    ) -> None:
        self._organization_repository = organization_repository
        self._membership_repository = membership_repository

    def execute(self, command: ListOrganizationsCommand) -> list[OrganizationResult]:
        memberships = self._membership_repository.list_by_user_id(command.user_id)
        results: list[OrganizationResult] = []
        seen: set[object] = set()

        for membership in memberships:
            if not membership.is_effective():
                continue
            organization_id = membership.organization_id
            if organization_id.value in seen:
                continue
            organization = self._organization_repository.get_by_id(organization_id)
            if organization is None:
                continue
            seen.add(organization_id.value)
            results.append(to_organization_result(organization))

        return sorted(results, key=lambda item: item.name.casefold())
