from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authorization.entities.role import Role
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.infrastructure.authorization.persistence.mappers.role_mapper import RoleMapper
from app.modules.identity.infrastructure.authorization.persistence.models.role import RoleModel


class SqlAlchemyRoleRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def add(self, role: Role) -> Role:
        model = RoleMapper.to_model(role)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return RoleMapper.to_domain(model)

    def update(self, role: Role) -> Role:
        model = self._session.get(RoleModel, role.id.value)
        if model is None:
            raise ValueError(f"Role not found: {role.id.value}")

        RoleMapper.apply_to_model(role, model)
        self._session.flush()
        self._session.refresh(model)
        return RoleMapper.to_domain(model)

    def remove(self, role_id: RoleId) -> None:
        model = self._session.get(RoleModel, role_id.value)
        if model is None:
            raise ValueError(f"Role not found: {role_id.value}")

        if model.deleted_at is not None:
            return

        model.deleted_at = datetime.now(tz=UTC)
        self._session.flush()

    def get_by_id(self, role_id: RoleId) -> Role | None:
        model = self._session.get(RoleModel, role_id.value)
        if model is None or model.deleted_at is not None:
            return None
        return RoleMapper.to_domain(model)

    def get_by_slug(self, slug: RoleSlug, scope: RoleScope) -> Role | None:
        stmt = select(RoleModel).where(
            RoleModel.slug == slug.value,
            RoleModel.scope == scope.value,
            RoleModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return RoleMapper.to_domain(model)

    def list_system_roles(self) -> list[Role]:
        stmt = select(RoleModel).where(
            RoleModel.is_system.is_(True),
            RoleModel.deleted_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [RoleMapper.to_domain(model) for model in models]
