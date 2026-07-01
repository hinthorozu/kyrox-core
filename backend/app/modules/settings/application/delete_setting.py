from app.modules.settings.application.commands import DeleteSettingCommand
from app.modules.settings.application.policy import SettingPolicy
from app.modules.settings.domain.exceptions import SettingNotFoundError
from app.modules.settings.domain.ports import SettingRepository


class DeleteSettingUseCase:
    def __init__(
        self,
        setting_repository: SettingRepository,
        setting_policy: SettingPolicy | None = None,
    ) -> None:
        self._setting_repository = setting_repository
        self._setting_policy = setting_policy or SettingPolicy()

    def execute(self, command: DeleteSettingCommand) -> None:
        self._setting_policy.validate_scope(command.scope, command.organization_id)
        key = self._setting_policy.normalize_key(command.key)
        deleted = self._setting_repository.delete(command.scope, command.organization_id, key)
        if not deleted:
            raise SettingNotFoundError(f"Setting not found: {key.value}")
