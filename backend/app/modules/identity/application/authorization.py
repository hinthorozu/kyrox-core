from uuid import UUID

from app.modules.identity.domain.enums import UserStatus
from app.modules.identity.domain.exceptions import PermissionDeniedError
from app.modules.identity.domain.ports import PermissionChecker, UserRepository

# Core super admins bypass role-based checks for core.* permissions only.
_CORE_PERMISSION_PREFIX = "core."


class AuthorizationService:
    def __init__(
        self,
        permission_checker: PermissionChecker,
        user_repository: UserRepository,
    ) -> None:
        self._permission_checker = permission_checker
        self._user_repository = user_repository

    def has_permission(
        self,
        user_id: UUID,
        organization_id: UUID,
        permission_code: str,
    ) -> bool:
        user = self._user_repository.get_by_id(user_id)
        if user is None or user.deleted_at is not None or user.status is not UserStatus.ACTIVE:
            return False

        if user.is_super_admin and permission_code.startswith(_CORE_PERMISSION_PREFIX):
            return True

        return self._permission_checker.has_permission(
            user_id=user_id,
            organization_id=organization_id,
            permission_code=permission_code,
        )

    def require_permission(
        self,
        user_id: UUID,
        organization_id: UUID,
        permission_code: str,
    ) -> None:
        if not self.has_permission(user_id, organization_id, permission_code):
            raise PermissionDeniedError(
                f"Permission denied: {permission_code} for organization {organization_id}"
            )
