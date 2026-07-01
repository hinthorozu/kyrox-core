from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.membership.entities.membership_invite import MembershipInvite
from app.modules.identity.domain.membership.value_objects.identity.invite_id import InviteId
from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.infrastructure.membership.persistence.mappers.membership_invite_mapper import (
    MembershipInviteMapper,
)
from app.modules.identity.infrastructure.membership.persistence.models.membership_invite import (
    MembershipInviteModel,
)


class SqlAlchemyMembershipInviteRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def add(self, invite: MembershipInvite) -> MembershipInvite:
        model = MembershipInviteMapper.to_model(invite)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return MembershipInviteMapper.to_domain(model)

    def update(self, invite: MembershipInvite) -> MembershipInvite:
        model = self._session.get(MembershipInviteModel, invite.id.value)
        if model is None:
            raise ValueError(f"Membership invite not found: {invite.id.value}")

        MembershipInviteMapper.apply_to_model(invite, model)
        self._session.flush()
        self._session.refresh(model)
        return MembershipInviteMapper.to_domain(model)

    def remove(self, invite_id: InviteId) -> None:
        model = self._session.get(MembershipInviteModel, invite_id.value)
        if model is None:
            raise ValueError(f"Membership invite not found: {invite_id.value}")

        self._session.delete(model)
        self._session.flush()

    def get_by_id(self, invite_id: InviteId) -> MembershipInvite | None:
        model = self._session.get(MembershipInviteModel, invite_id.value)
        if model is None:
            return None
        return MembershipInviteMapper.to_domain(model)

    def get_pending_by_token_hash(self, token_hash: InviteTokenHash) -> MembershipInvite | None:
        stmt = select(MembershipInviteModel).where(
            MembershipInviteModel.token_hash == token_hash.value,
            MembershipInviteModel.accepted_at.is_(None),
            MembershipInviteModel.revoked_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return MembershipInviteMapper.to_domain(model)

    def list_pending_by_organization_id(
        self,
        organization_id: OrganizationId,
    ) -> list[MembershipInvite]:
        stmt = select(MembershipInviteModel).where(
            MembershipInviteModel.organization_id == organization_id.value,
            MembershipInviteModel.accepted_at.is_(None),
            MembershipInviteModel.revoked_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [MembershipInviteMapper.to_domain(model) for model in models]
