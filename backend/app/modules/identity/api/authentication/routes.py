from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status

from app.modules.identity.api.authentication.access_guard import (
    get_authenticated_access_token_claims,
)
from app.modules.identity.api.authentication.dependencies import (
    get_change_password_use_case,
    get_complete_activation_use_case,
    get_forgot_password_use_case,
    get_logout_use_case,
    get_public_signup_use_case,
    get_reset_password_use_case,
)
from app.modules.identity.api.authentication.error_mapping import map_authentication_error
from app.modules.identity.api.authentication.lifecycle_dependencies import (
    get_lifecycle_aware_login_use_case,
    get_lifecycle_aware_refresh_session_use_case,
)
from app.modules.identity.api.authentication.mappers import (
    activation_request_to_command,
    change_password_request_to_command,
    forgot_password_request_to_command,
    login_request_to_command,
    logout_request_to_command,
    public_signup_request_to_command,
    refresh_request_to_command,
    reset_password_request_to_command,
    result_to_token_response,
)
from app.modules.identity.api.authentication.schemas import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    CompleteActivationRequest,
    CompleteActivationResponse,
    ErrorResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    PublicSignupRequest,
    PublicSignupResponse,
    RefreshRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
)
from app.modules.identity.application.authentication.activation import (
    CompleteActivationUseCase,
)
from app.modules.identity.application.authentication.login import LoginUseCase
from app.modules.identity.application.authentication.logout import LogoutUseCase
from app.modules.identity.application.authentication.password_change import ChangePasswordUseCase
from app.modules.identity.application.authentication.password_recovery import (
    ForgotPasswordUseCase,
    ResetPasswordUseCase,
)
from app.modules.identity.application.authentication.public_signup import PublicSignupUseCase
from app.modules.identity.application.authentication.refresh_session import RefreshSessionUseCase
from app.modules.identity.domain.authentication.exceptions import AuthenticationError
from app.modules.identity.domain.authentication.value_objects.security.access_token import (
    AccessTokenClaims,
)
from app.modules.notifications.api.dependencies import (
    NotificationWorkerScheduler,
    get_notification_worker_scheduler,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=PublicSignupResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def public_signup(
    payload: PublicSignupRequest,
    background_tasks: BackgroundTasks,
    use_case: PublicSignupUseCase = Depends(get_public_signup_use_case),
    worker_scheduler: NotificationWorkerScheduler = Depends(get_notification_worker_scheduler),
) -> PublicSignupResponse:
    try:
        use_case.execute(public_signup_request_to_command(payload))
    except AuthenticationError as exc:
        raise map_authentication_error(exc) from exc

    worker_scheduler.schedule(background_tasks)
    return PublicSignupResponse(
        message="Signup accepted. Check your email to activate your account."
    )


@router.post(
    "/activation/complete",
    response_model=CompleteActivationResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def complete_activation(
    payload: CompleteActivationRequest,
    use_case: CompleteActivationUseCase = Depends(get_complete_activation_use_case),
) -> CompleteActivationResponse:
    try:
        use_case.execute(activation_request_to_command(payload))
    except AuthenticationError as exc:
        raise map_authentication_error(exc) from exc

    return CompleteActivationResponse(
        message="Account activated. You can now sign in."
    )


@router.post(
    "/password/forgot",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    use_case: ForgotPasswordUseCase = Depends(get_forgot_password_use_case),
    worker_scheduler: NotificationWorkerScheduler = Depends(get_notification_worker_scheduler),
) -> ForgotPasswordResponse:
    use_case.execute(forgot_password_request_to_command(payload))
    worker_scheduler.schedule(background_tasks)
    return ForgotPasswordResponse(
        message="If the account can be recovered, password reset instructions will be sent."
    )


@router.post(
    "/password/reset",
    response_model=ResetPasswordResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def reset_password(
    payload: ResetPasswordRequest,
    use_case: ResetPasswordUseCase = Depends(get_reset_password_use_case),
) -> ResetPasswordResponse:
    try:
        use_case.execute(reset_password_request_to_command(payload))
    except AuthenticationError as exc:
        raise map_authentication_error(exc) from exc

    return ResetPasswordResponse(
        message="Password reset. Sign in with your new password."
    )


@router.post(
    "/password/change",
    response_model=ChangePasswordResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def change_password(
    payload: ChangePasswordRequest,
    claims: AccessTokenClaims = Depends(get_authenticated_access_token_claims),
    use_case: ChangePasswordUseCase = Depends(get_change_password_use_case),
) -> ChangePasswordResponse:
    try:
        use_case.execute(
            change_password_request_to_command(
                payload,
                user_id=claims.sub.value,
            )
        )
    except AuthenticationError as exc:
        raise map_authentication_error(exc) from exc

    return ChangePasswordResponse(
        message="Password changed. Sign in again with your new password."
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def login(
    payload: LoginRequest,
    request: Request,
    use_case: LoginUseCase = Depends(get_lifecycle_aware_login_use_case),
) -> TokenResponse:
    try:
        result = use_case.execute(login_request_to_command(payload, request))
    except AuthenticationError as exc:
        raise map_authentication_error(exc) from exc

    return result_to_token_response(result)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
def refresh(
    payload: RefreshRequest,
    use_case: RefreshSessionUseCase = Depends(get_lifecycle_aware_refresh_session_use_case),
) -> TokenResponse:
    try:
        result = use_case.execute(refresh_request_to_command(payload))
    except AuthenticationError as exc:
        raise map_authentication_error(exc) from exc

    return result_to_token_response(result)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Logged out successfully"}},
)
def logout(
    payload: LogoutRequest,
    use_case: LogoutUseCase = Depends(get_logout_use_case),
) -> Response:
    use_case.execute(logout_request_to_command(payload))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
