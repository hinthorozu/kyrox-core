from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.entities.membership import Membership
from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.infrastructure.membership.persistence.mappers.membership_mapper import (
    MembershipMapper,
)
from app.modules.identity.infrastructure.membership.persistence.models.membership import MembershipModel


class SqlAlchemyMembershipRepository:
    def __init__(self, session: DbSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def add(self, membership: Membership) -> Membership:
        model = MembershipMapper.to_model(membership)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return MembershipMapper.to_domain(model)

    def update(self, membership: Membership) -> Membership:
        model = self._session.get(MembershipModel, membership.id.value)
        if model is None:
            raise ValueError(f"Membership not found: {membership.id.value}")

        MembershipMapper.apply_to_model(membership, model)
        self._session.flush()
        self._session.refresh(model)
        return MembershipMapper.to_domain(model)

    def remove(self, membership_id: MembershipId) -> None:
        model = self._session.get(MembershipModel, membership_id.value)
        if model is None:
            raise ValueError(f"Membership not found: {membership_id.value}")

        if model.deleted_at is not None:
            return

        model.deleted_at = self._clock.now()
        self._session.flush()

    def get_by_id(self, membership_id: MembershipId) -> Membership | None:
        model = self._session.get(MembershipModel, membership_id.value)
        if model is None or model.deleted_at is not None:
            return None
        return MembershipMapper.to_domain(model)

    def get_by_user_and_organization(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> Membership | None:
        stmt = select(MembershipModel).where(
            MembershipModel.user_id == user_id.value,
            MembershipModel.organization_id == organization_id.value,
            MembershipModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return MembershipMapper.to_domain(model)

    def list_by_user_id(self, user_id: UserId) -> list[Membership]:
        stmt = select(MembershipModel).where(
            MembershipModel.user_id == user_id.value,
            MembershipModel.deleted_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [MembershipMapper.to_domain(model) for model in models]

    def list_by_organization_id(self, organization_id: OrganizationId) -> list[Membership]:
        stmt = select(MembershipModel).where(
            MembershipModel.organization_id == organization_id.value,
            MembershipModel.deleted_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [MembershipMapper.to_domain(model) for model in models]

    def list_effective_by_organization_id(
        self,
        organization_id: OrganizationId,
    ) -> list[Membership]:
        stmt = select(MembershipModel).where(
            MembershipModel.organization_id == organization_id.value,
            MembershipModel.status == MembershipStatus.ACTIVE.value,
            MembershipModel.deleted_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [MembershipMapper.to_domain(model) for model in models]
