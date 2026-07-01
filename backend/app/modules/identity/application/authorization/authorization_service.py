from app.modules.identity.application.authorization.commands import CheckPermissionCommand
from app.modules.identity.application.authorization.policy import PermissionPolicy, SuperAdminPolicy
from app.modules.identity.application.authorization.results import AuthorizationDecision
from app.modules.identity.domain.authorization.exceptions import PermissionDeniedError
from app.modules.identity.domain.authorization.ports.permission_checker import PermissionChecker
from app.modules.identity.domain.authorization.ports.platform_user_reader import PlatformUserReader


class AuthorizationService:
    def __init__(
        self,
        platform_user_reader: PlatformUserReader,
        permission_checker: PermissionChecker,
        super_admin_policy: SuperAdminPolicy | None = None,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self._platform_user_reader = platform_user_reader
        self._permission_checker = permission_checker
        self._super_admin_policy = super_admin_policy or SuperAdminPolicy()
        self._permission_policy = permission_policy or PermissionPolicy()

    def check_permission(self, command: CheckPermissionCommand) -> AuthorizationDecision:
        permission_code = self._permission_policy.normalize(command.permission_code)

        snapshot = self._platform_user_reader.get_snapshot(command.user_id)
        if snapshot is None or not snapshot.can_be_authorized():
            return AuthorizationDecision(
                allowed=False,
                permission_code=permission_code,
                denial_reason="user_not_authorizable",
            )

        if self._super_admin_policy.allows(snapshot, permission_code):
            return AuthorizationDecision(
                allowed=True,
                permission_code=permission_code,
                bypassed_by_super_admin=True,
            )

        allowed = self._permission_checker.has_permission(
            command.user_id,
            command.organization_id,
            permission_code,
        )
        if allowed:
            return AuthorizationDecision(
                allowed=True,
                permission_code=permission_code,
            )

        return AuthorizationDecision(
            allowed=False,
            permission_code=permission_code,
            denial_reason="permission_denied",
        )

    def has_permission(self, command: CheckPermissionCommand) -> bool:
        return self.check_permission(command).allowed

    def require_permission(self, command: CheckPermissionCommand) -> None:
        decision = self.check_permission(command)
        if decision.is_denied:
            raise PermissionDeniedError(
                f"Permission denied: {decision.permission_code.value} "
                f"for organization {command.organization_id.value}"
            )
