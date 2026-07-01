from dataclasses import dataclass

from app.modules.identity.domain.authorization.value_objects.rbac.permission_code import PermissionCode


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    permission_code: PermissionCode
    bypassed_by_super_admin: bool = False
    denial_reason: str | None = None

    @property
    def is_denied(self) -> bool:
        return not self.allowed
