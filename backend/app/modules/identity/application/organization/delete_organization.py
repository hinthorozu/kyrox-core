from datetime import UTC

from app.modules.identity.application.organization.commands import DeleteOrganizationCommand
from app.modules.identity.domain.organization.exceptions import (
    InactiveOrganizationError,
    OrganizationNotFoundError,
)
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository


class DeleteOrganizationUseCase:
    def __init__(self, organization_repository: OrganizationRepository) -> None:
        self._organization_repository = organization_repository

    def execute(self, command: DeleteOrganizationCommand) -> None:
        organization = self._organization_repository.get_by_id(command.organization_id)
        if organization is None:
            raise OrganizationNotFoundError("Organization not found")

        expected_updated_at = command.expected_suspension_updated_at
        if expected_updated_at is None:
            self._organization_repository.remove(command.organization_id)
            return

        if expected_updated_at.tzinfo is None or expected_updated_at.utcoffset() is None:
            raise InactiveOrganizationError(
                "Conditional organization tombstone requires a timezone-aware suspension episode"
            )

        removed = self._organization_repository.remove_if_suspended_episode(
            command.organization_id,
            expected_updated_at.astimezone(UTC),
        )
        if not removed:
            raise InactiveOrganizationError(
                "Organization is not in the expected suspended lifecycle episode"
            )
