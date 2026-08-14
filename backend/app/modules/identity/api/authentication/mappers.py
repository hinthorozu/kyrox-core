from fastapi import Request

from app.modules.identity.api.authentication.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from app.modules.identity.application.authentication.commands import (
    ClientContextCommand,
    LoginCommand,
    LogoutCommand,
    RefreshSessionCommand,
)
from app.modules.identity.application.authentication.results import AuthTokenPairResult
from app.modules.identity.domain.authentication.value_objects.security.refresh_token import (
    RefreshToken as RefreshTokenValue,
)


def login_request_to_command(payload: LoginRequest, request: Request) -> LoginCommand:
    client_ip = request.client.host if request.client else None
    return LoginCommand(
        email=str(payload.email),
        password=payload.password,
        client=ClientContextCommand(
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
        ),
    )


def refresh_request_to_command(payload: RefreshRequest) -> RefreshSessionCommand:
    return RefreshSessionCommand(
        refresh_token=RefreshTokenValue.create(payload.refresh_token),
    )


def logout_request_to_command(payload: LogoutRequest) -> LogoutCommand:
    return LogoutCommand(
        refresh_token=RefreshTokenValue.create(payload.refresh_token),
    )


def result_to_token_response(result: AuthTokenPairResult) -> TokenResponse:
    return TokenResponse(
        access_token=result.access_token.value,
        refresh_token=result.refresh_token.value,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )
