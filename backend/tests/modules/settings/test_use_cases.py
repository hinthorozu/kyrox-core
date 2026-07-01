import uuid
from datetime import UTC, datetime

import pytest

from app.modules.settings.application.commands import DeleteSettingCommand, GetSettingCommand
from app.modules.settings.application.delete_setting import DeleteSettingUseCase
from app.modules.settings.application.get_setting import GetSettingUseCase
from app.modules.settings.domain.entities import Setting
from app.modules.settings.domain.exceptions import SettingNotFoundError
from app.modules.settings.domain.value_objects.setting_key import SettingKey
from app.modules.settings.domain.value_objects.setting_scope import SettingScope


class FakeSettingRepository:
    def __init__(self, settings: list[Setting] | None = None) -> None:
        self._settings = settings or []

    def get(self, scope, organization_id, key):
        for setting in self._settings:
            if (
                setting.scope == scope
                and setting.organization_id == organization_id
                and setting.key.value == key.value
            ):
                return setting
        return None

    def list_by_scope(self, scope, organization_id, *, key_prefix=None):
        return [
            setting
            for setting in self._settings
            if setting.scope == scope and setting.organization_id == organization_id
        ]

    def upsert(self, setting):
        self._settings = [
            item
            for item in self._settings
            if not (
                item.scope == setting.scope
                and item.organization_id == setting.organization_id
                and item.key.value == setting.key.value
            )
        ]
        self._settings.append(setting)
        return setting

    def delete(self, scope, organization_id, key):
        before = len(self._settings)
        self._settings = [
            setting
            for setting in self._settings
            if not (
                setting.scope == scope
                and setting.organization_id == organization_id
                and setting.key.value == key.value
            )
        ]
        return len(self._settings) < before


def _sample_setting(org_id: uuid.UUID) -> Setting:
    now = datetime.now(UTC)
    return Setting(
        id=uuid.uuid4(),
        scope=SettingScope.ORGANIZATION,
        organization_id=org_id,
        key=SettingKey.create("fair_crm.pipeline.default_stage"),
        value={"enabled": True},
        created_at=now,
        updated_at=now,
    )


def test_get_setting_use_case_returns_result() -> None:
    org_id = uuid.uuid4()
    setting = _sample_setting(org_id)
    use_case = GetSettingUseCase(FakeSettingRepository([setting]))

    result = use_case.execute(
        GetSettingCommand(
            scope=SettingScope.ORGANIZATION,
            organization_id=org_id,
            key="fair_crm.pipeline.default_stage",
        )
    )

    assert result.key == "fair_crm.pipeline.default_stage"
    assert result.value == {"enabled": True}


def test_get_setting_use_case_raises_when_missing() -> None:
    use_case = GetSettingUseCase(FakeSettingRepository())
    with pytest.raises(SettingNotFoundError):
        use_case.execute(
            GetSettingCommand(
                scope=SettingScope.SYSTEM,
                organization_id=None,
                key="kyrox.platform.maintenance_mode",
            )
        )


def test_delete_setting_use_case_raises_when_missing() -> None:
    use_case = DeleteSettingUseCase(FakeSettingRepository())
    with pytest.raises(SettingNotFoundError):
        use_case.execute(
            DeleteSettingCommand(
                scope=SettingScope.SYSTEM,
                organization_id=None,
                key="kyrox.platform.maintenance_mode",
            )
        )
