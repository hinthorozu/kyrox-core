from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modules.identity.domain.membership.exceptions import DuplicateMembershipError
from app.modules.identity.domain.membership.value_objects.invite.invite_email import InviteEmail
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.exceptions import InactiveOrganizationError


@dataclass(frozen=True, slots=True)
class MembershipInvitePolicy:
    default_ttl_hours: int = 168

    def expires_at(self, now: datetime) -> datetime:
        return now + timedelta(hours=self.default_ttl_hours)

    def assert_can_invite(self, organization: Organization) -> None:
        if not organization.can_accept_members():
            raise InactiveOrganizationError("Organization cannot accept new members")


@dataclass(frozen=True, slots=True)
class DuplicateMembershipPolicy:
    def assert_no_pending_invite_for_email(
        self,
        *,
        email: InviteEmail,
        pending_invites: list,
        at: datetime,
    ) -> None:
        for invite in pending_invites:
            if invite.email.value == email.value and invite.is_pending(at):
                raise DuplicateMembershipError(
                    f"Pending invite already exists for {email.value}"
                )

    def assert_no_effective_membership(self, *, has_membership: bool, email: InviteEmail) -> None:
        if has_membership:
            raise DuplicateMembershipError(
                f"User is already a member of the organization: {email.value}"
            )
