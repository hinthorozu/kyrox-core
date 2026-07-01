from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authorization.entities.organization_role import OrganizationRole
from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.organization_role_id import (
    OrganizationRoleId,
)
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.infrastructure.authorization.persistence.mappers.organization_role_mapper import (
    OrganizationRoleMapper,
)
from app.modules.identity.infrastructure.authorization.persistence.models.organization_role import (
    OrganizationRoleModel,
)


class SqlAlchemyOrganizationRoleRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def add(self, organization_role: OrganizationRole) -> OrganizationRole:
        model = OrganizationRoleMapper.to_model(organization_role)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return OrganizationRoleMapper.to_domain(model)

    def update(self, organization_role: OrganizationRole) -> OrganizationRole:
        model = self._session.get(OrganizationRoleModel, organization_role.id.value)
        if model is None:
            raise ValueError(f"Organization role not found: {organization_role.id.value}")

        OrganizationRoleMapper.apply_to_model(organization_role, model)
        self._session.flush()
        self._session.refresh(model)
        return OrganizationRoleMapper.to_domain(model)

    def remove(self, organization_role_id: OrganizationRoleId) -> None:
        model = self._session.get(OrganizationRoleModel, organization_role_id.value)
        if model is None:
            raise ValueError(f"Organization role not found: {organization_role_id.value}")

        if model.deleted_at is not None:
            return

        model.deleted_at = datetime.now(tz=UTC)
        self._session.flush()

    def get_by_id(self, organization_role_id: OrganizationRoleId) -> OrganizationRole | None:
        model = self._session.get(OrganizationRoleModel, organization_role_id.value)
        if model is None:
            return None
        return OrganizationRoleMapper.to_domain(model)

    def get_by_organization_and_role(
        self,
        organization_id: OrganizationId,
        role_id: RoleId,
    ) -> OrganizationRole | None:
        stmt = select(OrganizationRoleModel).where(
            OrganizationRoleModel.organization_id == organization_id.value,
            OrganizationRoleModel.role_id == role_id.value,
            OrganizationRoleModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return OrganizationRoleMapper.to_domain(model)

    def list_active_by_organization(
        self,
        organization_id: OrganizationId,
    ) -> list[OrganizationRole]:
        stmt = select(OrganizationRoleModel).where(
            OrganizationRoleModel.organization_id == organization_id.value,
            OrganizationRoleModel.status == AssignmentStatus.ACTIVE.value,
            OrganizationRoleModel.deleted_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [OrganizationRoleMapper.to_domain(model) for model in models]
