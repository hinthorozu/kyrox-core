from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.authorization.guards import require_permission
from app.modules.identity.api.membership.dependencies import assert_organization_scope
from app.modules.settings.api.dependencies import (
    get_delete_setting_use_case,
    get_get_setting_use_case,
    get_list_settings_use_case,
    get_upsert_setting_use_case,
)
from app.modules.settings.api.error_mapping import map_setting_error
from app.modules.settings.api.guards import SuperAdminContext, require_super_admin
from app.modules.settings.api.mappers import (
    org_delete_command,
    org_get_command,
    org_list_command,
    org_upsert_command,
    setting_list_result_to_response,
    setting_result_to_response,
    system_delete_command,
    system_get_command,
    system_list_command,
    system_upsert_command,
)
from app.modules.settings.api.schemas import (
    ErrorResponse,
    SettingListResponse,
    SettingResponse,
    SettingUpsertRequest,
)
from app.modules.settings.application.delete_setting import DeleteSettingUseCase
from app.modules.settings.application.get_setting import GetSettingUseCase
from app.modules.settings.application.list_settings import ListSettingsUseCase
from app.modules.settings.application.upsert_setting import UpsertSettingUseCase
from app.modules.settings.domain.exceptions import SettingError

router = APIRouter(tags=["settings"])


def _handle_setting_errors(use_case_call):
    try:
        return use_case_call()
    except SettingError as exc:
        raise map_setting_error(exc) from exc


@router.get(
    "/organizations/{organization_id}/settings",
    response_model=SettingListResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def list_organization_settings(
    organization_id: UUID,
    key_prefix: str | None = Query(default=None),
    context: AuthorizationContext = Depends(require_permission("settings.platform.read")),
    use_case: ListSettingsUseCase = Depends(get_list_settings_use_case),
) -> SettingListResponse:
    assert_organization_scope(organization_id, context)
    result = _handle_setting_errors(
        lambda: use_case.execute(org_list_command(organization_id, key_prefix))
    )
    return setting_list_result_to_response(result)


@router.get(
    "/organizations/{organization_id}/settings/{setting_key:path}",
    response_model=SettingResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_organization_setting(
    organization_id: UUID,
    setting_key: str,
    context: AuthorizationContext = Depends(require_permission("settings.platform.read")),
    use_case: GetSettingUseCase = Depends(get_get_setting_use_case),
) -> SettingResponse:
    assert_organization_scope(organization_id, context)
    result = _handle_setting_errors(
        lambda: use_case.execute(org_get_command(organization_id, setting_key))
    )
    return setting_result_to_response(result)


@router.put(
    "/organizations/{organization_id}/settings/{setting_key:path}",
    response_model=SettingResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def upsert_organization_setting(
    organization_id: UUID,
    setting_key: str,
    body: SettingUpsertRequest,
    context: AuthorizationContext = Depends(require_permission("settings.platform.update")),
    use_case: UpsertSettingUseCase = Depends(get_upsert_setting_use_case),
) -> SettingResponse:
    assert_organization_scope(organization_id, context)
    result = _handle_setting_errors(
        lambda: use_case.execute(org_upsert_command(organization_id, setting_key, body))
    )
    return setting_result_to_response(result)


@router.delete(
    "/organizations/{organization_id}/settings/{setting_key:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def delete_organization_setting(
    organization_id: UUID,
    setting_key: str,
    context: AuthorizationContext = Depends(require_permission("settings.platform.update")),
    use_case: DeleteSettingUseCase = Depends(get_delete_setting_use_case),
) -> Response:
    assert_organization_scope(organization_id, context)
    _handle_setting_errors(lambda: use_case.execute(org_delete_command(organization_id, setting_key)))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/system/settings",
    response_model=SettingListResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def list_system_settings(
    key_prefix: str | None = Query(default=None),
    _context: SuperAdminContext = Depends(require_super_admin),
    use_case: ListSettingsUseCase = Depends(get_list_settings_use_case),
) -> SettingListResponse:
    result = _handle_setting_errors(lambda: use_case.execute(system_list_command(key_prefix)))
    return setting_list_result_to_response(result)


@router.get(
    "/system/settings/{setting_key:path}",
    response_model=SettingResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_system_setting(
    setting_key: str,
    _context: SuperAdminContext = Depends(require_super_admin),
    use_case: GetSettingUseCase = Depends(get_get_setting_use_case),
) -> SettingResponse:
    result = _handle_setting_errors(lambda: use_case.execute(system_get_command(setting_key)))
    return setting_result_to_response(result)


@router.put(
    "/system/settings/{setting_key:path}",
    response_model=SettingResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def upsert_system_setting(
    setting_key: str,
    body: SettingUpsertRequest,
    _context: SuperAdminContext = Depends(require_super_admin),
    use_case: UpsertSettingUseCase = Depends(get_upsert_setting_use_case),
) -> SettingResponse:
    result = _handle_setting_errors(
        lambda: use_case.execute(system_upsert_command(setting_key, body))
    )
    return setting_result_to_response(result)


@router.delete(
    "/system/settings/{setting_key:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def delete_system_setting(
    setting_key: str,
    _context: SuperAdminContext = Depends(require_super_admin),
    use_case: DeleteSettingUseCase = Depends(get_delete_setting_use_case),
) -> Response:
    _handle_setting_errors(lambda: use_case.execute(system_delete_command(setting_key)))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
