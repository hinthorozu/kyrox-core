from app.modules.identity.domain.authorization.entities.permission import Permission
from app.modules.identity.domain.authorization.value_objects.identity.permission_group_id import (
    PermissionGroupId,
)
from app.modules.identity.domain.authorization.value_objects.identity.permission_id import PermissionId
from app.modules.identity.domain.authorization.value_objects.rbac.permission_code import PermissionCode
from app.modules.identity.infrastructure.authorization.persistence.models.permission import PermissionModel


class PermissionMapper:
    @staticmethod
    def to_domain(model: PermissionModel) -> Permission:
        return Permission(
            id=PermissionId(model.id),
            group_id=PermissionGroupId(model.group_id),
            code=PermissionCode.create(model.code),
            description=model.description,
            is_system=model.is_system,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Permission) -> PermissionModel:
        return PermissionModel(
            id=entity.id.value,
            group_id=entity.group_id.value,
            code=entity.code.value,
            description=entity.description,
            is_system=entity.is_system,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def apply_to_model(entity: Permission, model: PermissionModel) -> None:
        model.group_id = entity.group_id.value
        model.code = entity.code.value
        model.description = entity.description
        model.is_system = entity.is_system
        model.updated_at = entity.updated_at
