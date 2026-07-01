from app.modules.settings.application.commands import ListSettingsCommand
from app.modules.settings.application.get_setting import _to_setting_result
from app.modules.settings.application.policy import SettingPolicy
from app.modules.settings.application.results import SettingListResult
from app.modules.settings.domain.ports import SettingRepository


class ListSettingsUseCase:
    def __init__(
        self,
        setting_repository: SettingRepository,
        setting_policy: SettingPolicy | None = None,
    ) -> None:
        self._setting_repository = setting_repository
        self._setting_policy = setting_policy or SettingPolicy()

    def execute(self, command: ListSettingsCommand) -> SettingListResult:
        self._setting_policy.validate_scope(command.scope, command.organization_id)
        key_prefix = self._setting_policy.validate_key_prefix(command.key_prefix)
        settings = self._setting_repository.list_by_scope(
            command.scope,
            command.organization_id,
            key_prefix=key_prefix,
        )
        return SettingListResult(items=[_to_setting_result(item) for item in settings])
