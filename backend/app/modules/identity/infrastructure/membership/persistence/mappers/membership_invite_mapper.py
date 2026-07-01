from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.entities.membership_invite import MembershipInvite
from app.modules.identity.domain.membership.value_objects.identity.invite_id import InviteId
from app.modules.identity.domain.membership.value_objects.invite.invite_email import InviteEmail
from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.infrastructure.membership.persistence.models.membership_invite import (
    MembershipInviteModel,
)


class MembershipInviteMapper:
    @staticmethod
    def to_domain(model: MembershipInviteModel) -> MembershipInvite:
        return MembershipInvite(
            id=InviteId(model.id),
            organization_id=OrganizationId(model.organization_id),
            email=InviteEmail(value=model.email),
            token_hash=InviteTokenHash(value=model.token_hash),
            invited_by_user_id=UserId(model.invited_by_user_id),
            expires_at=model.expires_at,
            accepted_at=model.accepted_at,
            revoked_at=model.revoked_at,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: MembershipInvite) -> MembershipInviteModel:
        return MembershipInviteModel(
            id=entity.id.value,
            organization_id=entity.organization_id.value,
            email=entity.email.value,
            token_hash=entity.token_hash.value,
            invited_by_user_id=entity.invited_by_user_id.value,
            expires_at=entity.expires_at,
            accepted_at=entity.accepted_at,
            revoked_at=entity.revoked_at,
            created_at=entity.created_at,
        )

    @staticmethod
    def apply_to_model(entity: MembershipInvite, model: MembershipInviteModel) -> None:
        model.organization_id = entity.organization_id.value
        model.email = entity.email.value
        model.token_hash = entity.token_hash.value
        model.invited_by_user_id = entity.invited_by_user_id.value
        model.expires_at = entity.expires_at
        model.accepted_at = entity.accepted_at
        model.revoked_at = entity.revoked_at
