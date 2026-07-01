from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.membership.commands import InviteMemberCommand
from app.modules.identity.application.membership.invite_token_issuer import InviteTokenIssuer
from app.modules.identity.application.membership.policy import (
    DuplicateMembershipPolicy,
    MembershipInvitePolicy,
)
from app.modules.identity.application.membership.results import InviteMemberResult
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.membership.entities.membership_invite import MembershipInvite
from app.modules.identity.domain.membership.ports.membership_invite_repository import (
    MembershipInviteRepository,
)
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository
from app.modules.identity.domain.membership.value_objects.identity.invite_id import InviteId
from app.modules.identity.domain.membership.value_objects.invite.invite_email import InviteEmail
from app.modules.identity.domain.organization.exceptions import OrganizationNotFoundError
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository


class InviteMemberUseCase:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        membership_invite_repository: MembershipInviteRepository,
        membership_repository: MembershipRepository,
        user_repository: UserRepository,
        invite_token_issuer: InviteTokenIssuer,
        clock: Clock,
        id_generator: IdGenerator,
        invite_policy: MembershipInvitePolicy | None = None,
        duplicate_policy: DuplicateMembershipPolicy | None = None,
    ) -> None:
        self._organization_repository = organization_repository
        self._membership_invite_repository = membership_invite_repository
        self._membership_repository = membership_repository
        self._user_repository = user_repository
        self._invite_token_issuer = invite_token_issuer
        self._clock = clock
        self._id_generator = id_generator
        self._invite_policy = invite_policy or MembershipInvitePolicy()
        self._duplicate_policy = duplicate_policy or DuplicateMembershipPolicy()

    def execute(self, command: InviteMemberCommand) -> InviteMemberResult:
        organization = self._organization_repository.get_by_id(command.organization_id)
        if organization is None:
            raise OrganizationNotFoundError(
                f"Organization not found: {command.organization_id.value}"
            )

        self._invite_policy.assert_can_invite(organization)
        email = InviteEmail.create(command.email)
        now = self._clock.now()

        pending_invites = self._membership_invite_repository.list_pending_by_organization_id(
            command.organization_id
        )
        self._duplicate_policy.assert_no_pending_invite_for_email(
            email=email,
            pending_invites=pending_invites,
            at=now,
        )

        existing_user = self._user_repository.get_by_email(Email.create(email.value))
        if existing_user is not None:
            existing_membership = self._membership_repository.get_by_user_and_organization(
                existing_user.id,
                command.organization_id,
            )
            if existing_membership is not None and existing_membership.is_effective():
                self._duplicate_policy.assert_no_effective_membership(
                    has_membership=True,
                    email=email,
                )

        token_hash, plain_token = self._invite_token_issuer.issue()
        invite = MembershipInvite(
            id=InviteId(self._id_generator.generate_uuid()),
            organization_id=command.organization_id,
            email=email,
            token_hash=token_hash,
            invited_by_user_id=command.invited_by_user_id,
            expires_at=self._invite_policy.expires_at(now),
            accepted_at=None,
            revoked_at=None,
            created_at=now,
        )
        invite = self._membership_invite_repository.add(invite)

        return InviteMemberResult(
            invite_id=invite.id,
            plain_token=plain_token,
            expires_at=invite.expires_at,
        )
