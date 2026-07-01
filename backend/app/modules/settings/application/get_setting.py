from app.modules.settings.application.commands import GetSettingCommand
from app.modules.settings.application.policy import SettingPolicy
from app.modules.settings.application.results import SettingResult
from app.modules.settings.domain.entities import Setting
from app.modules.settings.domain.exceptions import SettingNotFoundError
from app.modules.settings.domain.ports import SettingRepository


class GetSettingUseCase:
    def __init__(
        self,
        setting_repository: SettingRepository,
        setting_policy: SettingPolicy | None = None,
    ) -> None:
        self._setting_repository = setting_repository
        self._setting_policy = setting_policy or SettingPolicy()

    def execute(self, command: GetSettingCommand) -> SettingResult:
        self._setting_policy.validate_scope(command.scope, command.organization_id)
        key = self._setting_policy.normalize_key(command.key)
        setting = self._setting_repository.get(command.scope, command.organization_id, key)
        if setting is None:
            raise SettingNotFoundError(f"Setting not found: {key.value}")
        return _to_setting_result(setting)


def _to_setting_result(setting: Setting) -> SettingResult:
    return SettingResult(
        id=setting.id,
        scope=setting.scope.value,
        organization_id=setting.organization_id,
        key=setting.key.value,
        value=setting.value,
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )
