from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.value_objects.rbac.permission_code import PermissionCode
from app.modules.identity.domain.enums import OrganizationStatus
from app.modules.identity.infrastructure.authorization.persistence.models.permission import PermissionModel
from app.modules.identity.infrastructure.authorization.persistence.models.role import RoleModel
from app.modules.identity.infrastructure.authorization.persistence.models.role_permission import (
    RolePermissionModel,
)
from app.modules.identity.infrastructure.authorization.persistence.models.user_role import UserRoleModel
from app.modules.identity.infrastructure.persistence.models import OrganizationModel, UserModel


class SqlAlchemyPermissionChecker:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def has_permission(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
        permission_code: PermissionCode,
    ) -> bool:
        """Resolve an organization-scoped permission from the active RBAC graph."""
        stmt = (
            select(PermissionModel.id)
            .join(
                RolePermissionModel,
                RolePermissionModel.permission_id == PermissionModel.id,
            )
            .join(RoleModel, RoleModel.id == RolePermissionModel.role_id)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .join(UserModel, UserModel.id == UserRoleModel.user_id)
            .join(OrganizationModel, OrganizationModel.id == UserRoleModel.organization_id)
            .where(
                UserModel.id == user_id.value,
                UserModel.status == "active",
                UserModel.deleted_at.is_(None),
                UserModel.is_super_admin.is_(False),
                UserRoleModel.user_id == user_id.value,
                UserRoleModel.organization_id == organization_id.value,
                UserRoleModel.status == AssignmentStatus.ACTIVE.value,
                UserRoleModel.revoked_at.is_(None),
                RoleModel.deleted_at.is_(None),
                RoleModel.is_assignable.is_(True),
                (RoleModel.organization_id.is_(None) | (RoleModel.organization_id == organization_id.value)),
                OrganizationModel.status == OrganizationStatus.ACTIVE.value,
                OrganizationModel.deleted_at.is_(None),
                PermissionModel.code == permission_code.value,
                PermissionModel.lifecycle_state == "active",
                PermissionModel.permission_scope == "organization",
            )
        )
        return self._session.scalars(stmt).first() is not None
