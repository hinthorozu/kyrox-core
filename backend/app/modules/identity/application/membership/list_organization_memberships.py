from app.modules.identity.application.membership.commands import ListOrganizationMembershipsCommand
from app.modules.identity.application.membership.mappers import to_membership_result
from app.modules.identity.application.membership.results import MembershipListResult
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository
from app.modules.identity.domain.organization.exceptions import OrganizationNotFoundError
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository


class ListOrganizationMembershipsUseCase:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        membership_repository: MembershipRepository,
    ) -> None:
        self._organization_repository = organization_repository
        self._membership_repository = membership_repository

    def execute(self, command: ListOrganizationMembershipsCommand) -> MembershipListResult:
        organization = self._organization_repository.get_by_id(command.organization_id)
        if organization is None:
            raise OrganizationNotFoundError(
                f"Organization not found: {command.organization_id.value}"
            )

        memberships = self._membership_repository.list_by_organization_id(command.organization_id)
        return MembershipListResult(
            memberships=[to_membership_result(membership) for membership in memberships]
        )
