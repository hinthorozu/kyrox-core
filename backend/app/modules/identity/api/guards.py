from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AppException
from app.modules.identity.api.context import AuthorizationContext
from app.modules.identity.api.dependencies import get_authorization_service, get_token_service
from app.modules.identity.application.authorization import AuthorizationService
from app.modules.identity.domain.exceptions import PermissionDeniedError
from app.modules.identity.domain.ports import AccessTokenClaims, TokenService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_access_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token_service: TokenService = Depends(get_token_service),
) -> AccessTokenClaims:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppException("Not authenticated", status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        return token_service.decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
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
        user_id=claims.sub,
        organization_id=organization_id,
        email=claims.email,
    )


def require_permission(
    permission_code: str,
) -> Callable[..., AuthorizationContext]:
    def dependency(
        context: AuthorizationContext = Depends(get_authorization_context),
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> AuthorizationContext:
        try:
            authorization_service.require_permission(
                user_id=context.user_id,
                organization_id=context.organization_id,
                permission_code=permission_code,
            )
        except PermissionDeniedError as exc:
            raise AppException(str(exc), status_code=status.HTTP_403_FORBIDDEN) from exc

        return context

    return dependency
