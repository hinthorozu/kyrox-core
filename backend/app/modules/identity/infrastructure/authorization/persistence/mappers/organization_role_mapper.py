from app.modules.identity.domain.authorization.entities.organization_role import OrganizationRole
from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.organization_role_id import (
    OrganizationRoleId,
)
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.infrastructure.authorization.persistence.models.organization_role import (
    OrganizationRoleModel,
)


class OrganizationRoleMapper:
    @staticmethod
    def to_domain(model: OrganizationRoleModel) -> OrganizationRole:
        return OrganizationRole(
            id=OrganizationRoleId(model.id),
            organization_id=OrganizationId(model.organization_id),
            role_id=RoleId(model.role_id),
            status=AssignmentStatus(model.status),
            is_default=model.is_default,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(entity: OrganizationRole) -> OrganizationRoleModel:
        return OrganizationRoleModel(
            id=entity.id.value,
            organization_id=entity.organization_id.value,
            role_id=entity.role_id.value,
            status=entity.status.value,
            is_default=entity.is_default,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    @staticmethod
    def apply_to_model(entity: OrganizationRole, model: OrganizationRoleModel) -> None:
        model.organization_id = entity.organization_id.value
        model.role_id = entity.role_id.value
        model.status = entity.status.value
        model.is_default = entity.is_default
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at
