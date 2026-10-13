from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import JSONResponse

from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.authorization.guards import require_permission, require_super_admin
from app.modules.identity.domain.authentication.value_objects.security.access_token import AccessTokenClaims
from app.modules.identity.api.authorization.scope import assert_organization_scope
from app.modules.notifications.api.dependencies import (
    NotificationWorkerScheduler,
    get_get_notification_use_case,
    get_notification_worker_scheduler,
    get_send_notification_use_case,
    get_list_system_in_app_notifications_use_case,
    require_product_notification_credential,
)
from app.modules.notifications.api.error_mapping import map_notification_error
from app.modules.notifications.api.mappers import (
    get_notification_command,
    get_result_to_response,
    send_request_to_command,
    send_result_to_response,
)
from app.modules.notifications.api.schemas import (
    ErrorResponse,
    NotificationResponse,
    SendNotificationRequest,
    SendNotificationResponse,
)
from app.modules.notifications.application.get_notification import GetNotificationUseCase
from app.modules.notifications.application.send_notification import SendNotificationUseCase
from app.modules.notifications.application.list_in_app_notifications import ListSystemInAppNotificationsUseCase
from app.modules.notifications.application.commands import SendNotificationCommand
from app.modules.notifications.api.schemas import InAppNotificationResponse, SystemInAppNotificationRequest
from app.modules.notifications.domain.exceptions import NotificationError
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus

router = APIRouter(tags=["notifications"])


@router.post("/system/notifications/in-app", response_model=SendNotificationResponse)
def send_system_in_app_notification(
    body: SystemInAppNotificationRequest,
    _: AccessTokenClaims = Depends(require_super_admin),
    use_case: SendNotificationUseCase = Depends(get_send_notification_use_case),
) -> SendNotificationResponse:
    result = _handle_notification_errors(lambda: use_case.execute(SendNotificationCommand(
        organization_id=None, channel="in_app", recipient=body.recipient,
        subject=body.subject, body=body.body, variables=body.variables,
        template_key=None, idempotency_key=body.idempotency_key,
    )))
    return send_result_to_response(result)


@router.get("/system/notifications/in-app", response_model=list[InAppNotificationResponse])
def list_system_in_app_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    claims: AccessTokenClaims = Depends(require_super_admin),
    use_case: ListSystemInAppNotificationsUseCase = Depends(get_list_system_in_app_notifications_use_case),
) -> list[InAppNotificationResponse]:
    return [InAppNotificationResponse(
        id=item.id, subject=item.subject, body=item.body,
        variables=item.variables, created_at=item.created_at,
    ) for item in use_case.execute(claims.sub.value, limit=limit)]


@router.post("/internal/notifications/in-app", response_model=SendNotificationResponse,
             dependencies=[Depends(require_product_notification_credential)])
def deliver_worker_in_app_notification(
    body: SystemInAppNotificationRequest,
    use_case: SendNotificationUseCase = Depends(get_send_notification_use_case),
) -> SendNotificationResponse:
    result = _handle_notification_errors(lambda: use_case.execute(SendNotificationCommand(
        organization_id=None, channel="in_app", recipient=body.recipient,
        subject=body.subject, body=body.body, variables=body.variables,
        template_key=None, idempotency_key=body.idempotency_key,
    )))
    return send_result_to_response(result)


def _handle_notification_errors(use_case_call):
    try:
        return use_case_call()
    except NotificationError as exc:
        raise map_notification_error(exc) from exc


@router.post(
    "/organizations/{organization_id}/notifications/send",
    response_model=SendNotificationResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def send_organization_notification(
    organization_id: UUID,
    body: SendNotificationRequest,
    background_tasks: BackgroundTasks,
    context: AuthorizationContext = Depends(require_permission("notifications.platform.execute")),
    use_case: SendNotificationUseCase = Depends(get_send_notification_use_case),
    worker_scheduler: NotificationWorkerScheduler = Depends(get_notification_worker_scheduler),
) -> JSONResponse:
    assert_organization_scope(organization_id, context)
    result = _handle_notification_errors(
        lambda: use_case.execute(send_request_to_command(organization_id, body))
    )
    if result.status == NotificationStatus.QUEUED:
        worker_scheduler.schedule(background_tasks)
    response = send_result_to_response(result)
    status_code = (
        status.HTTP_200_OK
        if result.idempotent_replay
        else status.HTTP_202_ACCEPTED
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


@router.get(
    "/notifications/{notification_id}",
    response_model=NotificationResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_notification_status(
    notification_id: UUID,
    context: AuthorizationContext = Depends(require_permission("notifications.platform.read")),
    use_case: GetNotificationUseCase = Depends(get_get_notification_use_case),
) -> NotificationResponse:
    result = _handle_notification_errors(
        lambda: use_case.execute(
            get_notification_command(
                notification_id,
                None if context.is_super_admin else context.organization_id,
            )
        )
    )
    return get_result_to_response(result)
