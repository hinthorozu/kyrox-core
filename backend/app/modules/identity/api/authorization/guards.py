from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AppException
from app.modules.identity.api.authentication.dependencies import get_token_service
from app.modules.identity.api.authorization.context import (
    AuthenticatedOrganizationContext,
    AuthorizationContext,
)
from app.modules.identity.api.authorization.dependencies import (
    get_authorization_service,
    get_membership_repository,
    get_platform_user_reader,
)
from app.modules.identity.api.authorization.error_mapping import map_authorization_error
from app.modules.identity.application.authorization import AuthorizationService, CheckPermissionCommand
from app.modules.identity.domain.authentication.ports.token_service import TokenService
from app.modules.identity.domain.authentication.value_objects.security.access_token import (
    AccessToken,
    AccessTokenClaims,
)
from app.modules.identity.domain.authorization.exceptions import PermissionDeniedError
from app.modules.identity.domain.authorization.ports.platform_user_reader import PlatformUserReader
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId as MembershipOrganizationId,
)

_bearer_scheme = HTTPBearer(auto_error=False)


def get_access_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token_service: TokenService = Depends(get_token_service),
) -> AccessTokenClaims:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppException("Not authenticated", status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        return token_service.decode_access_token(AccessToken.create(credentials.credentials))
    except (jwt.PyJWTError, ValueError) as exc:
        raise AppException("Invalid access token", status_code=status.HTTP_401_UNAUTHORIZED) from exc


def get_organization_id(
    x_organization_id: Annotated[UUID, Header(alias="X-Organization-Id")],
) -> UUID:
    return x_organization_id


def get_authorization_context(
    claims: AccessTokenClaims = Depends(get_access_token_claims),
    organization_id: UUID = Depends(get_organization_id),
) -> AuthorizationContext:
    return AuthorizationContext(
        user_id=claims.sub.value,
        organization_id=organization_id,
        email=claims.email.value,
    )


def _assert_active_membership(
    claims: AccessTokenClaims,
    organization_id: UUID,
    membership_repository: MembershipRepository,
    platform_user_reader: PlatformUserReader,
) -> None:
    snapshot = platform_user_reader.get_snapshot(claims.sub)
    if snapshot is not None and snapshot.is_super_admin:
        return

    membership = membership_repository.get_by_user_and_organization(
        claims.sub,
        MembershipOrganizationId(organization_id),
    )
    if membership is None or not membership.is_effective():
        raise AppException("Forbidden", status_code=status.HTTP_403_FORBIDDEN)


def require_organization_membership() -> Callable[..., AuthenticatedOrganizationContext]:
    def dependency(
        claims: AccessTokenClaims = Depends(get_access_token_claims),
        organization_id: UUID = Depends(get_organization_id),
        membership_repository: MembershipRepository = Depends(get_membership_repository),
        platform_user_reader: PlatformUserReader = Depends(get_platform_user_reader),
    ) -> AuthenticatedOrganizationContext:
        _assert_active_membership(
            claims,
            organization_id,
            membership_repository,
            platform_user_reader,
        )
        return AuthenticatedOrganizationContext(
            user_id=claims.sub.value,
            organization_id=organization_id,
            email=claims.email.value,
            session_id=claims.sid.value,
        )

    return dependency


def require_permission(
    permission_code: str,
) -> Callable[..., AuthorizationContext]:
    def dependency(
        context: AuthorizationContext = Depends(get_authorization_context),
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> AuthorizationContext:
        try:
            authorization_service.require_permission(
                CheckPermissionCommand(
                    user_id=UserId(context.user_id),
                    organization_id=OrganizationId(context.organization_id),
                    permission_code=permission_code,
                )
            )
        except PermissionDeniedError as exc:
            raise map_authorization_error(exc) from exc

        return context

    return dependency
