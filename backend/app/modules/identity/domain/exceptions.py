class AuthenticationError(Exception):
    """Base class for authentication failures."""


class InvalidCredentialsError(AuthenticationError):
    """Email or password is invalid."""


class InactiveUserError(AuthenticationError):
    """User account is not active."""


class InvalidRefreshTokenError(AuthenticationError):
    """Refresh token is missing, invalid, expired, or revoked."""


class AuthorizationError(Exception):
    """Base class for authorization failures."""


class PermissionDeniedError(AuthorizationError):
    """User lacks the required permission in the organization context."""
