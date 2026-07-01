from typing import Protocol

from app.modules.identity.domain.membership.entities.membership_invite import MembershipInvite
from app.modules.identity.domain.membership.value_objects.identity.invite_id import InviteId
from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


class MembershipInviteRepository(Protocol):
    def add(self, invite: MembershipInvite) -> MembershipInvite: ...

    def update(self, invite: MembershipInvite) -> MembershipInvite: ...

    def remove(self, invite_id: InviteId) -> None: ...

    def get_by_id(self, invite_id: InviteId) -> MembershipInvite | None: ...

    def get_pending_by_token_hash(self, token_hash: InviteTokenHash) -> MembershipInvite | None: ...

    def list_pending_by_organization_id(
        self,
        organization_id: OrganizationId,
    ) -> list[MembershipInvite]: ...
