from dataclasses import dataclass

from app.modules.identity.domain.authentication.value_objects.security.refresh_token import (
    RefreshToken as RefreshTokenValue,
)


@dataclass(frozen=True, slots=True)
class ClientContextCommand:
    ip_address: str | None = None
    user_agent: str | None = None
    device_name: str | None = None
    client_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str
    client: ClientContextCommand | None = None


@dataclass(frozen=True, slots=True)
class RefreshSessionCommand:
    refresh_token: RefreshTokenValue
    client: ClientContextCommand | None = None


@dataclass(frozen=True, slots=True)
class LogoutCommand:
    refresh_token: RefreshTokenValue
