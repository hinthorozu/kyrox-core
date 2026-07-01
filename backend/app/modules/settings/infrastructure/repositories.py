from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.modules.settings.domain.entities import Setting
from app.modules.settings.domain.value_objects.setting_key import SettingKey
from app.modules.settings.domain.value_objects.setting_scope import SettingScope
from app.modules.settings.infrastructure.persistence.mappers import setting_to_domain, setting_to_model
from app.modules.settings.infrastructure.persistence.models import PlatformSettingModel


class SqlAlchemySettingRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def get(
        self,
        scope: SettingScope,
        organization_id: UUID | None,
        key: SettingKey,
    ) -> Setting | None:
        stmt = (
            select(PlatformSettingModel)
            .where(PlatformSettingModel.scope == scope.value)
            .where(_organization_filter(organization_id))
            .where(PlatformSettingModel.key == key.value)
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return setting_to_domain(model)

    def list_by_scope(
        self,
        scope: SettingScope,
        organization_id: UUID | None,
        *,
        key_prefix: str | None = None,
    ) -> list[Setting]:
        stmt = (
            select(PlatformSettingModel)
            .where(PlatformSettingModel.scope == scope.value)
            .where(_organization_filter(organization_id))
            .order_by(PlatformSettingModel.key.asc())
        )
        if key_prefix is not None:
            escaped = _escape_like_prefix(key_prefix)
            stmt = stmt.where(PlatformSettingModel.key.like(f"{escaped}%", escape="\\"))
        models = self._session.scalars(stmt).all()
        return [setting_to_domain(model) for model in models]

    def upsert(self, setting: Setting) -> Setting:
        existing = self.get(setting.scope, setting.organization_id, setting.key)
        if existing is None:
            model = setting_to_model(setting)
            self._session.add(model)
            self._session.flush()
            return setting_to_domain(model)

        stmt = (
            select(PlatformSettingModel)
            .where(PlatformSettingModel.scope == setting.scope.value)
            .where(_organization_filter(setting.organization_id))
            .where(PlatformSettingModel.key == setting.key.value)
        )
        model = self._session.scalars(stmt).one()
        model.value = setting.value
        model.updated_at = setting.updated_at
        self._session.flush()
        return setting_to_domain(model)

    def delete(
        self,
        scope: SettingScope,
        organization_id: UUID | None,
        key: SettingKey,
    ) -> bool:
        stmt = (
            delete(PlatformSettingModel)
            .where(PlatformSettingModel.scope == scope.value)
            .where(_organization_filter(organization_id))
            .where(PlatformSettingModel.key == key.value)
        )
        result = self._session.execute(stmt)
        return result.rowcount > 0


def _organization_filter(organization_id: UUID | None):
    if organization_id is None:
        return PlatformSettingModel.organization_id.is_(None)
    return PlatformSettingModel.organization_id == organization_id


def _escape_like_prefix(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
