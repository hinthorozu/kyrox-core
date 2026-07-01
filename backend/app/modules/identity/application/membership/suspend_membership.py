from app.modules.identity.application.membership.commands import RemoveMembershipCommand, SuspendMembershipCommand
from app.modules.identity.application.membership.mappers import to_membership_result
from app.modules.identity.application.membership.results import MembershipResult
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.membership.exceptions import MembershipNotFoundError
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository


class SuspendMembershipUseCase:
    def __init__(
        self,
        membership_repository: MembershipRepository,
        clock: Clock,
    ) -> None:
        self._membership_repository = membership_repository
        self._clock = clock

    def execute(self, command: SuspendMembershipCommand) -> MembershipResult:
        membership = self._membership_repository.get_by_id(command.membership_id)
        if membership is None:
            raise MembershipNotFoundError(f"Membership not found: {command.membership_id.value}")

        membership.suspend(self._clock.now())
        membership = self._membership_repository.update(membership)
        return to_membership_result(membership)


class RemoveMembershipUseCase:
    def __init__(
        self,
        membership_repository: MembershipRepository,
        clock: Clock,
    ) -> None:
        self._membership_repository = membership_repository
        self._clock = clock

    def execute(self, command: RemoveMembershipCommand) -> MembershipResult:
        membership = self._membership_repository.get_by_id(command.membership_id)
        if membership is None:
            raise MembershipNotFoundError(f"Membership not found: {command.membership_id.value}")

        membership.remove(self._clock.now())
        membership = self._membership_repository.update(membership)
        return to_membership_result(membership)
