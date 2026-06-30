from fastapi import APIRouter, Depends, Request, Response, status

from app.core.exceptions import AppException
from app.modules.identity.api.dependencies import (
    get_login_use_case,
    get_logout_use_case,
    get_refresh_session_use_case,
)
from app.modules.identity.api.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from app.modules.identity.application.auth import (
    LoginUseCase,
    LogoutUseCase,
    RefreshSessionUseCase,
)
from app.modules.identity.application.dto import AuthTokenPair
from app.modules.identity.domain.exceptions import (
    AuthenticationError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_token_response(token_pair: AuthTokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


def _map_auth_error(exc: AuthenticationError) -> AppException:
    if isinstance(exc, InvalidCredentialsError):
        return AppException(str(exc), status_code=401)
    if isinstance(exc, InactiveUserError):
        return AppException(str(exc), status_code=403)
    if isinstance(exc, InvalidRefreshTokenError):
        return AppException(str(exc), status_code=401)
    return AppException(str(exc), status_code=401)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> TokenResponse:
    try:
        token_pair = use_case.execute(
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except AuthenticationError as exc:
        raise _map_auth_error(exc) from exc

    return _to_token_response(token_pair)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    use_case: RefreshSessionUseCase = Depends(get_refresh_session_use_case),
) -> TokenResponse:
    try:
        token_pair = use_case.execute(refresh_token=payload.refresh_token)
    except AuthenticationError as exc:
        raise _map_auth_error(exc) from exc

    return _to_token_response(token_pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    use_case: LogoutUseCase = Depends(get_logout_use_case),
) -> Response:
    use_case.execute(refresh_token=payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
