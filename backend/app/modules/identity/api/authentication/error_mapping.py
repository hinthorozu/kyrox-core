from app.core.exceptions import AppException
from app.modules.identity.domain.authentication.exceptions import (
    AuthenticationError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    LockedUserError,
)


def map_authentication_error(exc: AuthenticationError) -> AppException:
    if isinstance(exc, InvalidCredentialsError):
        return AppException("Invalid email or password", status_code=401)
    if isinstance(exc, InactiveUserError):
        return AppException(str(exc), status_code=403)
    if isinstance(exc, LockedUserError):
        return AppException(str(exc), status_code=403)
    if isinstance(exc, InvalidRefreshTokenError):
        return AppException("Invalid refresh token", status_code=401)
    return AppException(str(exc), status_code=401)
