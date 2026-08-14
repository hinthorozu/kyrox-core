from app.modules.identity.domain.authorization.entities.role import Role
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import OrganizationId
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
            role_kind=model.role_kind,
            organization_id=OrganizationId(model.organization_id) if model.organization_id else None,
            source_template_role_id=RoleId(model.source_template_role_id) if model.source_template_role_id else None,
            template_version=model.template_version,
            source_template_version=model.source_template_version,
            permissions_customized=model.permissions_customized,
            is_assignable=model.is_assignable,
            is_protected=model.is_protected,
            auto_include_new_permissions=model.auto_include_new_permissions,
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
            role_kind=entity.role_kind,
            organization_id=entity.organization_id.value if entity.organization_id else None,
            source_template_role_id=entity.source_template_role_id.value if entity.source_template_role_id else None,
            template_version=entity.template_version,
            source_template_version=entity.source_template_version,
            permissions_customized=entity.permissions_customized,
            is_assignable=entity.is_assignable,
            is_protected=entity.is_protected,
            auto_include_new_permissions=entity.auto_include_new_permissions,
        )

    @staticmethod
    def apply_to_model(entity: Role, model: RoleModel) -> None:
        model.name = entity.name
        model.slug = entity.slug.value
        model.scope = entity.scope.value
        model.is_system = entity.is_system
        model.role_kind = entity.role_kind
        model.organization_id = entity.organization_id.value if entity.organization_id else None
        model.source_template_role_id = entity.source_template_role_id.value if entity.source_template_role_id else None
        model.template_version = entity.template_version
        model.source_template_version = entity.source_template_version
        model.permissions_customized = entity.permissions_customized
        model.is_assignable = entity.is_assignable
        model.is_protected = entity.is_protected
        model.auto_include_new_permissions = entity.auto_include_new_permissions
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at
