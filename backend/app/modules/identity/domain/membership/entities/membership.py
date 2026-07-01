from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.exceptions import InvalidMembershipTransitionError
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


@dataclass
class Membership:
    id: MembershipId
    user_id: UserId
    organization_id: OrganizationId
    status: MembershipStatus
    invited_at: datetime | None
    joined_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def is_effective(self) -> bool:
        return not self.is_deleted() and self.status is MembershipStatus.ACTIVE

    def is_invited(self) -> bool:
        return not self.is_deleted() and self.status is MembershipStatus.INVITED

    def accept_invite(self, at: datetime) -> None:
        if not self.is_invited():
            raise InvalidMembershipTransitionError("Only invited memberships can be accepted")
        self.status = MembershipStatus.ACTIVE
        self.joined_at = at
        self.updated_at = at

    def suspend(self, at: datetime) -> None:
        if self.status is not MembershipStatus.ACTIVE:
            raise InvalidMembershipTransitionError("Only active memberships can be suspended")
        self.status = MembershipStatus.SUSPENDED
        self.updated_at = at

    def remove(self, at: datetime) -> None:
        if self.status is MembershipStatus.REMOVED:
            raise InvalidMembershipTransitionError("Membership is already removed")
        self.status = MembershipStatus.REMOVED
        self.updated_at = at

    def assert_can_access_organization(self) -> None:
        if not self.is_effective():
            raise InvalidMembershipTransitionError("Membership is not active")
