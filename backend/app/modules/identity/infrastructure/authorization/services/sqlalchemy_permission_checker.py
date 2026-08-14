from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.value_objects.rbac.permission_code import PermissionCode
from app.modules.identity.domain.enums import OrganizationStatus
from app.modules.identity.infrastructure.authorization.persistence.models.organization_role import (
    OrganizationRoleModel,
)
from app.modules.identity.infrastructure.authorization.persistence.models.permission import PermissionModel
from app.modules.identity.infrastructure.authorization.persistence.models.role import RoleModel
from app.modules.identity.infrastructure.authorization.persistence.models.role_permission import (
    RolePermissionModel,
)
from app.modules.identity.infrastructure.authorization.persistence.models.user_role import UserRoleModel
from app.modules.identity.infrastructure.membership.persistence.models import MembershipModel
from app.modules.identity.infrastructure.persistence.models import OrganizationModel

ORGANIZATION_ADMIN_ROLE_SLUG = "organization_admin"


class SqlAlchemyPermissionChecker:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def _is_organization_admin(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> bool:
        """Return True for an active OrganizationAdmin in this exact organization.

        This check intentionally does not depend on identity_permissions or
        identity_role_permissions. OrganizationAdmin is the full-access role
        inside its own organization, including permissions introduced by new
        modules before permission seed data exists.
        """
        stmt = (
            select(UserRoleModel.user_id)
            .join(
                OrganizationRoleModel,
                OrganizationRoleModel.id == UserRoleModel.organization_role_id,
            )
            .join(RoleModel, RoleModel.id == OrganizationRoleModel.role_id)
            .join(
                MembershipModel,
                (MembershipModel.user_id == UserRoleModel.user_id)
                & (MembershipModel.organization_id == UserRoleModel.organization_id),
            )
            .join(OrganizationModel, OrganizationModel.id == UserRoleModel.organization_id)
            .where(
                UserRoleModel.user_id == user_id.value,
                UserRoleModel.organization_id == organization_id.value,
                UserRoleModel.status == AssignmentStatus.ACTIVE.value,
                UserRoleModel.revoked_at.is_(None),
                OrganizationRoleModel.organization_id == organization_id.value,
                OrganizationRoleModel.status == AssignmentStatus.ACTIVE.value,
                OrganizationRoleModel.deleted_at.is_(None),
                RoleModel.slug == ORGANIZATION_ADMIN_ROLE_SLUG,
                RoleModel.deleted_at.is_(None),
                MembershipModel.status == "active",
                MembershipModel.deleted_at.is_(None),
                OrganizationModel.status == OrganizationStatus.ACTIVE.value,
                OrganizationModel.deleted_at.is_(None),
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first() is not None

    def has_permission(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
        permission_code: PermissionCode,
    ) -> bool:
        # OrganizationAdmin is god-mode only inside its own organization.
        # This bypass happens before permission-row lookup, so a missing or
        # newly introduced permission cannot block the organization admin.
        if self._is_organization_admin(user_id, organization_id):
            return True

        stmt = (
            select(PermissionModel.id)
            .join(
                RolePermissionModel,
                RolePermissionModel.permission_id == PermissionModel.id,
            )
            .join(RoleModel, RoleModel.id == RolePermissionModel.role_id)
            .join(OrganizationRoleModel, OrganizationRoleModel.role_id == RoleModel.id)
            .join(UserRoleModel, UserRoleModel.organization_role_id == OrganizationRoleModel.id)
            .join(OrganizationModel, OrganizationModel.id == UserRoleModel.organization_id)
            .where(
                UserRoleModel.user_id == user_id.value,
                UserRoleModel.organization_id == organization_id.value,
                UserRoleModel.status == AssignmentStatus.ACTIVE.value,
                UserRoleModel.revoked_at.is_(None),
                OrganizationRoleModel.organization_id == organization_id.value,
                OrganizationRoleModel.status == AssignmentStatus.ACTIVE.value,
                OrganizationRoleModel.deleted_at.is_(None),
                RoleModel.deleted_at.is_(None),
                OrganizationModel.status == OrganizationStatus.ACTIVE.value,
                OrganizationModel.deleted_at.is_(None),
                PermissionModel.code == permission_code.value,
            )
        )
        return self._session.scalars(stmt).first() is not None
