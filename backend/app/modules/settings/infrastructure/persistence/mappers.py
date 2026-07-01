from app.modules.settings.domain.entities import Setting
from app.modules.settings.domain.value_objects.setting_key import SettingKey
from app.modules.settings.domain.value_objects.setting_scope import SettingScope
from app.modules.settings.infrastructure.persistence.models import PlatformSettingModel


def setting_to_domain(model: PlatformSettingModel) -> Setting:
    return Setting(
        id=model.id,
        scope=SettingScope(model.scope),
        organization_id=model.organization_id,
        key=SettingKey(value=model.key),
        value=model.value,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def setting_to_model(entity: Setting) -> PlatformSettingModel:
    return PlatformSettingModel(
        id=entity.id,
        scope=entity.scope.value,
        organization_id=entity.organization_id,
        key=entity.key.value,
        value=entity.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
