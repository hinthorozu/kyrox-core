from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, status

from app.core.exceptions import AppException
from app.modules.identity.api.authorization.dependencies import get_platform_user_reader
from app.modules.identity.api.authorization.guards import get_access_token_claims
from app.modules.identity.domain.authentication.value_objects.security.access_token import AccessTokenClaims
from app.modules.identity.domain.authorization.ports.platform_user_reader import PlatformUserReader
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId


@dataclass(frozen=True, slots=True)
class SuperAdminContext:
    user_id: UUID
    email: str


def require_super_admin(
    claims: AccessTokenClaims = Depends(get_access_token_claims),
    reader: PlatformUserReader = Depends(get_platform_user_reader),
) -> SuperAdminContext:
    snapshot = reader.get_snapshot(UserId(claims.sub.value))
    if snapshot is None or not snapshot.can_be_authorized() or not snapshot.is_super_admin:
        raise AppException("Super admin required", status_code=status.HTTP_403_FORBIDDEN)
    return SuperAdminContext(user_id=claims.sub.value, email=claims.email.value)
