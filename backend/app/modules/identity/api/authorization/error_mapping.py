from app.core.exceptions import AppException
from app.modules.identity.domain.authorization.exceptions import (
    AuthorizationError,
    InvalidPermissionError,
    PermissionDeniedError,
)


def map_authorization_error(exc: AuthorizationError) -> AppException:
    if isinstance(exc, InvalidPermissionError):
        return AppException(str(exc), status_code=400)
    if isinstance(exc, PermissionDeniedError):
        return AppException(str(exc), status_code=403)
    return AppException(str(exc), status_code=403)
