from app.core.exceptions import AppException
from app.modules.identity.domain.authentication.exceptions import (
    AuthenticationError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    LockedUserError,
)
from app.modules.identity.domain.authentication.exceptions.authentication import (
    ActivationPasswordPolicyError,
    InvalidActivationTokenError,
    InvalidPasswordResetTokenError,
    PasswordResetPolicyError,
    PublicSignupConflictError,
    PublicSignupProvisioningError,
    PublicSignupValidationError,
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
    if isinstance(exc, PublicSignupValidationError):
        return AppException("Invalid signup details", status_code=422)
    if isinstance(exc, PublicSignupConflictError):
        return AppException(
            "An account with the supplied details already exists",
            status_code=409,
        )
    if isinstance(exc, PublicSignupProvisioningError):
        return AppException("Signup is temporarily unavailable", status_code=503)
    if isinstance(exc, InvalidActivationTokenError):
        return AppException("Invalid or expired activation token", status_code=400)
    if isinstance(exc, ActivationPasswordPolicyError):
        return AppException(
            "Password does not satisfy the Core password policy",
            status_code=422,
        )
    if isinstance(exc, InvalidPasswordResetTokenError):
        return AppException("Invalid or expired password reset token", status_code=400)
    if isinstance(exc, PasswordResetPolicyError):
        return AppException(
            "Password does not satisfy the Core password policy",
            status_code=422,
        )
    return AppException(str(exc), status_code=401)
