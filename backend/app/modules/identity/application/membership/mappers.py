from app.modules.identity.application.membership.results import MembershipResult
from app.modules.identity.domain.membership.entities.membership import Membership


def to_membership_result(membership: Membership) -> MembershipResult:
    return MembershipResult(
        membership_id=membership.id,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        status=membership.status,
        joined_at=membership.joined_at,
    )
