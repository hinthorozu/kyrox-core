class AuthenticationError(Exception):
    """Base class for authentication failures."""


class InvalidCredentialsError(AuthenticationError):
    """Email or password is invalid."""


class InactiveUserError(AuthenticationError):
    """User account is not active."""


class InvalidRefreshTokenError(AuthenticationError):
    """Refresh token is missing, invalid, expired, or revoked."""
