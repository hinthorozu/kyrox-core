from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authorization.entities.permission import Permission
from app.modules.identity.domain.authorization.value_objects.identity.permission_group_id import (
    PermissionGroupId,
)
from app.modules.identity.domain.authorization.value_objects.identity.permission_id import PermissionId
from app.modules.identity.domain.authorization.value_objects.rbac.permission_code import PermissionCode
from app.modules.identity.infrastructure.authorization.persistence.mappers.permission_mapper import (
    PermissionMapper,
)
from app.modules.identity.infrastructure.authorization.persistence.models.permission import PermissionModel


class SqlAlchemyPermissionRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def add(self, permission: Permission) -> Permission:
        model = PermissionMapper.to_model(permission)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return PermissionMapper.to_domain(model)

    def update(self, permission: Permission) -> Permission:
        model = self._session.get(PermissionModel, permission.id.value)
        if model is None:
            raise ValueError(f"Permission not found: {permission.id.value}")

        PermissionMapper.apply_to_model(permission, model)
        self._session.flush()
        self._session.refresh(model)
        return PermissionMapper.to_domain(model)

    def remove(self, permission_id: PermissionId) -> None:
        model = self._session.get(PermissionModel, permission_id.value)
        if model is None:
            raise ValueError(f"Permission not found: {permission_id.value}")

        self._session.delete(model)
        self._session.flush()

    def get_by_id(self, permission_id: PermissionId) -> Permission | None:
        model = self._session.get(PermissionModel, permission_id.value)
        if model is None:
            return None
        return PermissionMapper.to_domain(model)

    def get_by_code(self, code: PermissionCode) -> Permission | None:
        stmt = select(PermissionModel).where(PermissionModel.code == code.value)
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return PermissionMapper.to_domain(model)

    def list_by_group_id(self, group_id: PermissionGroupId) -> list[Permission]:
        stmt = select(PermissionModel).where(PermissionModel.group_id == group_id.value)
        models = self._session.scalars(stmt).all()
        return [PermissionMapper.to_domain(model) for model in models]

    def list_all(self) -> list[Permission]:
        models = self._session.scalars(select(PermissionModel)).all()
        return [PermissionMapper.to_domain(model) for model in models]
