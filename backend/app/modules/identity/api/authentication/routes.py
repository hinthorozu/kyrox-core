from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status

from app.modules.identity.api.authentication.dependencies import (
    get_complete_activation_use_case,
    get_login_use_case,
    get_logout_use_case,
    get_public_signup_use_case,
    get_refresh_session_use_case,
)
from app.modules.identity.api.authentication.error_mapping import map_authentication_error
from app.modules.identity.api.authentication.mappers import (
    activation_request_to_command,
    login_request_to_command,
    logout_request_to_command,
    public_signup_request_to_command,
    refresh_request_to_command,
    result_to_token_response,
)
from app.modules.identity.api.authentication.schemas import (
    CompleteActivationRequest,
    CompleteActivationResponse,
    ErrorResponse,
    LoginRequest,
    LogoutRequest,
    PublicSignupRequest,
    PublicSignupResponse,
    RefreshRequest,
    TokenResponse,
)
from app.modules.identity.application.authentication.activation import (
    CompleteActivationUseCase,
)
from app.modules.identity.application.authentication.login import LoginUseCase
from app.modules.identity.application.authentication.logout import LogoutUseCase
from app.modules.identity.application.authentication.public_signup import PublicSignupUseCase
from app.modules.identity.application.authentication.refresh_session import RefreshSessionUseCase
from app.modules.identity.domain.authentication.exceptions import AuthenticationError
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
    use_case: LoginUseCase = Depends(get_login_use_case),
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
    use_case: RefreshSessionUseCase = Depends(get_refresh_session_use_case),
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
