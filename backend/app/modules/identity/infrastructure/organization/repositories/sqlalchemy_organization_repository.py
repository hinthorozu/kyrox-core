from sqlalchemy import exists, select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import OrganizationSlug
from app.modules.identity.infrastructure.organization.persistence.mappers.organization_mapper import (
    OrganizationMapper,
)
from app.modules.identity.infrastructure.organization.persistence.models.organization import (
    OrganizationModel,
)


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: DbSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def add(self, organization: Organization) -> Organization:
        model = OrganizationMapper.to_model(organization)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return OrganizationMapper.to_domain(model)

    def update(self, organization: Organization) -> Organization:
        model = self._session.get(OrganizationModel, organization.id.value)
        if model is None:
            raise ValueError(f"Organization not found: {organization.id.value}")

        OrganizationMapper.apply_to_model(organization, model)
        self._session.flush()
        self._session.refresh(model)
        return OrganizationMapper.to_domain(model)

    def remove(self, organization_id: OrganizationId) -> None:
        model = self._session.get(OrganizationModel, organization_id.value)
        if model is None:
            raise ValueError(f"Organization not found: {organization_id.value}")

        if model.deleted_at is not None:
            return

        model.deleted_at = self._clock.now()
        self._session.flush()

    def get_by_id(self, organization_id: OrganizationId) -> Organization | None:
        model = self._session.get(OrganizationModel, organization_id.value)
        if model is None or model.deleted_at is not None:
            return None
        return OrganizationMapper.to_domain(model)

    def get_by_slug(self, slug: OrganizationSlug) -> Organization | None:
        stmt = select(OrganizationModel).where(
            OrganizationModel.slug == slug.value,
            OrganizationModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return OrganizationMapper.to_domain(model)

    def exists_by_slug(self, slug: OrganizationSlug) -> bool:
        stmt = select(
            exists().where(
                OrganizationModel.slug == slug.value,
                OrganizationModel.deleted_at.is_(None),
            )
        )
        return bool(self._session.scalar(stmt))
