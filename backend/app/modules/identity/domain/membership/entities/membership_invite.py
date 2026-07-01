from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.exceptions import (
    MembershipInviteAlreadyAcceptedError,
    MembershipInviteExpiredError,
)
from app.modules.identity.domain.membership.value_objects.identity.invite_id import InviteId
from app.modules.identity.domain.membership.value_objects.invite.invite_email import InviteEmail
from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


@dataclass
class MembershipInvite:
    id: InviteId
    organization_id: OrganizationId
    email: InviteEmail
    token_hash: InviteTokenHash
    invited_by_user_id: UserId
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    def is_expired(self, at: datetime) -> bool:
        return at >= self.expires_at

    def is_pending(self, at: datetime) -> bool:
        return (
            self.accepted_at is None
            and self.revoked_at is None
            and not self.is_expired(at)
        )

    def accept(self, at: datetime) -> None:
        if self.accepted_at is not None:
            raise MembershipInviteAlreadyAcceptedError("Invite was already accepted")
        if self.revoked_at is not None:
            raise MembershipInviteExpiredError("Invite is no longer valid")
        if self.is_expired(at):
            raise MembershipInviteExpiredError("Invite has expired")
        self.accepted_at = at

    def revoke(self, at: datetime) -> None:
        if self.accepted_at is not None:
            raise MembershipInviteAlreadyAcceptedError("Accepted invites cannot be revoked")
        self.revoked_at = at
