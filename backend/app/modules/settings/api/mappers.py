from uuid import UUID

from app.modules.settings.application.commands import (
    DeleteSettingCommand,
    GetSettingCommand,
    ListSettingsCommand,
    UpsertSettingCommand,
)
from app.modules.settings.application.results import SettingListResult, SettingResult
from app.modules.settings.api.schemas import SettingListResponse, SettingResponse, SettingUpsertRequest
from app.modules.settings.domain.value_objects.setting_scope import SettingScope


def org_get_command(organization_id: UUID, setting_key: str) -> GetSettingCommand:
    return GetSettingCommand(
        scope=SettingScope.ORGANIZATION,
        organization_id=organization_id,
        key=setting_key,
    )


def org_list_command(organization_id: UUID, key_prefix: str | None) -> ListSettingsCommand:
    return ListSettingsCommand(
        scope=SettingScope.ORGANIZATION,
        organization_id=organization_id,
        key_prefix=key_prefix,
    )


def org_upsert_command(
    organization_id: UUID,
    setting_key: str,
    body: SettingUpsertRequest,
) -> UpsertSettingCommand:
    return UpsertSettingCommand(
        scope=SettingScope.ORGANIZATION,
        organization_id=organization_id,
        key=setting_key,
        value=body.value,
    )


def org_delete_command(organization_id: UUID, setting_key: str) -> DeleteSettingCommand:
    return DeleteSettingCommand(
        scope=SettingScope.ORGANIZATION,
        organization_id=organization_id,
        key=setting_key,
    )


def system_get_command(setting_key: str) -> GetSettingCommand:
    return GetSettingCommand(
        scope=SettingScope.SYSTEM,
        organization_id=None,
        key=setting_key,
    )


def system_list_command(key_prefix: str | None) -> ListSettingsCommand:
    return ListSettingsCommand(
        scope=SettingScope.SYSTEM,
        organization_id=None,
        key_prefix=key_prefix,
    )


def system_upsert_command(setting_key: str, body: SettingUpsertRequest) -> UpsertSettingCommand:
    return UpsertSettingCommand(
        scope=SettingScope.SYSTEM,
        organization_id=None,
        key=setting_key,
        value=body.value,
    )


def system_delete_command(setting_key: str) -> DeleteSettingCommand:
    return DeleteSettingCommand(
        scope=SettingScope.SYSTEM,
        organization_id=None,
        key=setting_key,
    )


def setting_result_to_response(result: SettingResult) -> SettingResponse:
    return SettingResponse(
        id=result.id,
        scope=result.scope,
        organization_id=result.organization_id,
        key=result.key,
        value=result.value,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def setting_list_result_to_response(result: SettingListResult) -> SettingListResponse:
    return SettingListResponse(
        items=[setting_result_to_response(item) for item in result.items],
    )
