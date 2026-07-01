from datetime import UTC, datetime
from uuid import uuid4

from app.modules.settings.application.commands import UpsertSettingCommand
from app.modules.settings.application.get_setting import _to_setting_result
from app.modules.settings.application.policy import SettingPolicy
from app.modules.settings.application.results import SettingResult
from app.modules.settings.domain.entities import Setting
from app.modules.settings.domain.ports import SettingRepository


class UpsertSettingUseCase:
    def __init__(
        self,
        setting_repository: SettingRepository,
        setting_policy: SettingPolicy | None = None,
    ) -> None:
        self._setting_repository = setting_repository
        self._setting_policy = setting_policy or SettingPolicy()

    def execute(self, command: UpsertSettingCommand) -> SettingResult:
        self._setting_policy.validate_scope(command.scope, command.organization_id)
        key = self._setting_policy.normalize_key(command.key)
        value = self._setting_policy.validate_value(command.value)

        existing = self._setting_repository.get(command.scope, command.organization_id, key)
        now = datetime.now(UTC)
        if existing is None:
            setting = Setting(
                id=uuid4(),
                scope=command.scope,
                organization_id=command.organization_id,
                key=key,
                value=value,
                created_at=now,
                updated_at=now,
            )
        else:
            setting = Setting(
                id=existing.id,
                scope=existing.scope,
                organization_id=existing.organization_id,
                key=existing.key,
                value=value,
                created_at=existing.created_at,
                updated_at=now,
            )

        saved = self._setting_repository.upsert(setting)
        return _to_setting_result(saved)
