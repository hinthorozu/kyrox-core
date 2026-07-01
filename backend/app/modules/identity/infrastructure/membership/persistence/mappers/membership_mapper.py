from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.entities.membership import Membership
from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.infrastructure.membership.persistence.models.membership import MembershipModel


class MembershipMapper:
    @staticmethod
    def to_domain(model: MembershipModel) -> Membership:
        return Membership(
            id=MembershipId(model.id),
            user_id=UserId(model.user_id),
            organization_id=OrganizationId(model.organization_id),
            status=MembershipStatus(model.status),
            invited_at=model.invited_at,
            joined_at=model.joined_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(entity: Membership) -> MembershipModel:
        return MembershipModel(
            id=entity.id.value,
            user_id=entity.user_id.value,
            organization_id=entity.organization_id.value,
            status=entity.status.value,
            invited_at=entity.invited_at,
            joined_at=entity.joined_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    @staticmethod
    def apply_to_model(entity: Membership, model: MembershipModel) -> None:
        model.user_id = entity.user_id.value
        model.organization_id = entity.organization_id.value
        model.status = entity.status.value
        model.invited_at = entity.invited_at
        model.joined_at = entity.joined_at
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at
