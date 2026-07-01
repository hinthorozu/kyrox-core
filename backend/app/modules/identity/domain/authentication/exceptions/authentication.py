class AuthenticationError(Exception):
    """Base class for authentication failures."""


class InvalidCredentialsError(AuthenticationError):
    """Email or password is invalid."""


class InactiveUserError(AuthenticationError):
    """User account is not active."""


class LockedUserError(AuthenticationError):
    """User account is locked."""


class InvalidRefreshTokenError(AuthenticationError):
    """Refresh token is missing, malformed, or otherwise invalid."""


class ExpiredRefreshTokenError(InvalidRefreshTokenError):
    """Refresh token has expired."""


class RevokedRefreshTokenError(InvalidRefreshTokenError):
    """Refresh token has been revoked."""
