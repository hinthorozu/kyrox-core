from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse

from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.authorization.guards import require_permission
from app.modules.identity.api.membership.dependencies import assert_organization_scope
from app.modules.notifications.api.dependencies import (
    NotificationWorkerScheduler,
    get_get_notification_use_case,
    get_notification_worker_scheduler,
    get_send_notification_use_case,
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
from app.modules.notifications.domain.exceptions import NotificationError
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus

router = APIRouter(tags=["notifications"])


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
    context: AuthorizationContext = Depends(require_permission("notifications.platform.send")),
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
        lambda: use_case.execute(get_notification_command(notification_id, context.organization_id))
    )
    return get_result_to_response(result)
