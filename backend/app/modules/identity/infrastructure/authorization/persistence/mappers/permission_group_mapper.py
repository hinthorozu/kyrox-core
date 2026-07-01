from app.modules.identity.domain.authorization.entities.permission_group import PermissionGroup
from app.modules.identity.domain.authorization.value_objects.identity.permission_group_id import (
    PermissionGroupId,
)
from app.modules.identity.domain.authorization.value_objects.rbac.permission_group_code import (
    PermissionGroupCode,
)
from app.modules.identity.domain.authorization.value_objects.rbac.permission_module import (
    PermissionModule,
)
from app.modules.identity.infrastructure.authorization.persistence.models.permission_group import (
    PermissionGroupModel,
)


class PermissionGroupMapper:
    @staticmethod
    def to_domain(model: PermissionGroupModel) -> PermissionGroup:
        return PermissionGroup(
            id=PermissionGroupId(model.id),
            code=PermissionGroupCode.create(model.code),
            name=model.name,
            module=PermissionModule.create(model.module),
            description=model.description,
            sort_order=model.sort_order,
            is_system=model.is_system,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: PermissionGroup) -> PermissionGroupModel:
        return PermissionGroupModel(
            id=entity.id.value,
            code=entity.code.value,
            name=entity.name,
            module=entity.module.value,
            description=entity.description,
            sort_order=entity.sort_order,
            is_system=entity.is_system,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def apply_to_model(entity: PermissionGroup, model: PermissionGroupModel) -> None:
        model.code = entity.code.value
        model.name = entity.name
        model.module = entity.module.value
        model.description = entity.description
        model.sort_order = entity.sort_order
        model.is_system = entity.is_system
        model.updated_at = entity.updated_at
