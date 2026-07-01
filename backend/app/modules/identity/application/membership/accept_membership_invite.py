from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.membership.commands import AcceptMembershipInviteCommand
from app.modules.identity.application.membership.invite_token_issuer import InviteTokenIssuer
from app.modules.identity.application.membership.mappers import to_membership_result
from app.modules.identity.application.membership.results import AcceptMembershipInviteResult
from app.modules.identity.application.membership.role_assignment import MembershipRoleAssigner
from app.modules.identity.domain.authentication.exceptions import InactiveUserError
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.membership.entities.membership import Membership
from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.exceptions import MembershipInviteExpiredError
from app.modules.identity.domain.membership.ports.membership_invite_repository import (
    MembershipInviteRepository,
)
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId


class AcceptMembershipInviteUseCase:
    def __init__(
        self,
        membership_invite_repository: MembershipInviteRepository,
        membership_repository: MembershipRepository,
        user_repository: UserRepository,
        role_assigner: MembershipRoleAssigner,
        invite_token_issuer: InviteTokenIssuer,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._membership_invite_repository = membership_invite_repository
        self._membership_repository = membership_repository
        self._user_repository = user_repository
        self._role_assigner = role_assigner
        self._invite_token_issuer = invite_token_issuer
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, command: AcceptMembershipInviteCommand) -> AcceptMembershipInviteResult:
        user = self._user_repository.get_by_id(command.accepting_user_id)
        if user is None:
            raise InactiveUserError("Accepting user not found")
        user.assert_can_authenticate()

        token_hash = self._invite_token_issuer.hash_plain_token(command.plain_token)
        invite = self._membership_invite_repository.get_pending_by_token_hash(token_hash)
        if invite is None:
            raise MembershipInviteExpiredError("Invite not found or no longer valid")

        if invite.email.value != user.email.value:
            raise MembershipInviteExpiredError("Invite email does not match accepting user")

        now = self._clock.now()
        invite.accept(now)
        self._membership_invite_repository.update(invite)

        existing_membership = self._membership_repository.get_by_user_and_organization(
            command.accepting_user_id,
            invite.organization_id,
        )
        if existing_membership is not None and existing_membership.is_invited():
            existing_membership.accept_invite(now)
            membership = self._membership_repository.update(existing_membership)
        elif existing_membership is not None and existing_membership.is_effective():
            membership = existing_membership
        else:
            membership = Membership(
                id=MembershipId(self._id_generator.generate_uuid()),
                user_id=command.accepting_user_id,
                organization_id=invite.organization_id,
                status=MembershipStatus.ACTIVE,
                invited_at=invite.created_at,
                joined_at=now,
                created_at=now,
                updated_at=now,
            )
            membership = self._membership_repository.add(membership)

        self._role_assigner.assign_default_member_role(
            user_id=command.accepting_user_id,
            organization_id=invite.organization_id,
            assigned_by=invite.invited_by_user_id,
        )

        return AcceptMembershipInviteResult(
            membership=to_membership_result(membership),
            organization_id=invite.organization_id,
        )
