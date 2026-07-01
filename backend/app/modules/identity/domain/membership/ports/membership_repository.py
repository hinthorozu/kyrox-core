from typing import Protocol

from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.entities.membership import Membership
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


class MembershipRepository(Protocol):
    def add(self, membership: Membership) -> Membership: ...

    def update(self, membership: Membership) -> Membership: ...

    def remove(self, membership_id: MembershipId) -> None: ...

    def get_by_id(self, membership_id: MembershipId) -> Membership | None: ...

    def get_by_user_and_organization(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> Membership | None: ...

    def list_by_user_id(self, user_id: UserId) -> list[Membership]: ...

    def list_by_organization_id(self, organization_id: OrganizationId) -> list[Membership]: ...

    def list_effective_by_organization_id(
        self,
        organization_id: OrganizationId,
    ) -> list[Membership]: ...
