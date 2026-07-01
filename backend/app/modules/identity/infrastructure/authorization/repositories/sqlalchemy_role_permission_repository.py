from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authorization.entities.role_permission import RolePermission
from app.modules.identity.domain.authorization.value_objects.identity.permission_id import PermissionId
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.infrastructure.authorization.persistence.models.role_permission import (
    RolePermissionModel,
)


class SqlAlchemyRolePermissionRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def grant(self, role_permission: RolePermission) -> None:
        model = RolePermissionModel(
            role_id=role_permission.role_id.value,
            permission_id=role_permission.permission_id.value,
        )
        self._session.merge(model)
        self._session.flush()

    def revoke(self, role_id: RoleId, permission_id: PermissionId) -> None:
        model = self._session.get(
            RolePermissionModel,
            {"role_id": role_id.value, "permission_id": permission_id.value},
        )
        if model is not None:
            self._session.delete(model)
            self._session.flush()

    def list_permission_ids_for_role(self, role_id: RoleId) -> list[PermissionId]:
        stmt = select(RolePermissionModel.permission_id).where(
            RolePermissionModel.role_id == role_id.value
        )
        return [PermissionId(permission_id) for permission_id in self._session.scalars(stmt).all()]

    def has_permission(self, role_id: RoleId, permission_id: PermissionId) -> bool:
        model = self._session.get(
            RolePermissionModel,
            {"role_id": role_id.value, "permission_id": permission_id.value},
        )
        return model is not None
