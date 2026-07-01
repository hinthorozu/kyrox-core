class AuthorizationError(Exception):
    """Base class for authorization failures."""


class PermissionDeniedError(AuthorizationError):
    """User lacks the required permission in the organization context."""


class InvalidRoleError(AuthorizationError):
    """Role definition or assignment is invalid."""


class InvalidPermissionError(AuthorizationError):
    """Permission definition or assignment is invalid."""
