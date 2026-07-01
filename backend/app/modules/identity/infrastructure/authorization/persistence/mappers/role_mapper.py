from app.modules.identity.domain.authorization.entities.role import Role
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.infrastructure.authorization.persistence.models.role import RoleModel


class RoleMapper:
    @staticmethod
    def to_domain(model: RoleModel) -> Role:
        return Role(
            id=RoleId(model.id),
            name=model.name,
            slug=RoleSlug.create(model.slug),
            scope=RoleScope(model.scope),
            is_system=model.is_system,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(entity: Role) -> RoleModel:
        return RoleModel(
            id=entity.id.value,
            name=entity.name,
            slug=entity.slug.value,
            scope=entity.scope.value,
            is_system=entity.is_system,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    @staticmethod
    def apply_to_model(entity: Role, model: RoleModel) -> None:
        model.name = entity.name
        model.slug = entity.slug.value
        model.scope = entity.scope.value
        model.is_system = entity.is_system
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at
