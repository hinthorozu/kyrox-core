from app.modules.identity.domain.authorization.entities.user_role import UserRole
from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.organization_role_id import (
    OrganizationRoleId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.value_objects.identity.user_role_id import UserRoleId
from app.modules.identity.infrastructure.authorization.persistence.models.user_role import UserRoleModel


class UserRoleMapper:
    @staticmethod
    def to_domain(model: UserRoleModel) -> UserRole:
        return UserRole(
            id=UserRoleId(model.id),
            user_id=UserId(model.user_id),
            organization_id=OrganizationId(model.organization_id),
            organization_role_id=OrganizationRoleId(model.organization_role_id),
            status=AssignmentStatus(model.status),
            assigned_at=model.assigned_at,
            revoked_at=model.revoked_at,
            assigned_by=UserId(model.assigned_by) if model.assigned_by is not None else None,
        )

    @staticmethod
    def to_model(entity: UserRole) -> UserRoleModel:
        return UserRoleModel(
            id=entity.id.value,
            user_id=entity.user_id.value,
            organization_id=entity.organization_id.value,
            organization_role_id=entity.organization_role_id.value,
            status=entity.status.value,
            assigned_at=entity.assigned_at,
            revoked_at=entity.revoked_at,
            assigned_by=entity.assigned_by.value if entity.assigned_by is not None else None,
        )

    @staticmethod
    def apply_to_model(entity: UserRole, model: UserRoleModel) -> None:
        model.user_id = entity.user_id.value
        model.organization_id = entity.organization_id.value
        model.organization_role_id = entity.organization_role_id.value
        model.status = entity.status.value
        model.assigned_at = entity.assigned_at
        model.revoked_at = entity.revoked_at
        model.assigned_by = entity.assigned_by.value if entity.assigned_by is not None else None
