from typing import Any
from uuid import UUID

from app.modules.notifications.application.ports.setting_reader_port import OrganizationSettingReaderPort
from app.modules.notifications.domain.ports import OrganizationNotificationSettings
from app.modules.settings.domain.ports import SettingRepository
from app.modules.settings.domain.value_objects.setting_key import SettingKey
from app.modules.settings.domain.value_objects.setting_scope import SettingScope

EMAIL_ENABLED_KEY = "kyrox.notifications.email_enabled"
EMAIL_FROM_KEY = "kyrox.notifications.email_from"


class SettingRepositoryOrganizationSettingReader(OrganizationSettingReaderPort):
    """Reads organization settings through the settings module repository port."""

    def __init__(self, setting_repository: SettingRepository) -> None:
        self._setting_repository = setting_repository

    def get_organization_setting_value(
        self,
        organization_id: UUID,
        key: str,
    ) -> Any | None:
        setting = self._setting_repository.get(
            SettingScope.ORGANIZATION,
            organization_id,
            SettingKey.create(key),
        )
        if setting is None:
            return None
        return setting.value


class NotificationSettingsReaderAdapter:
    def __init__(self, setting_reader: OrganizationSettingReaderPort) -> None:
        self._setting_reader = setting_reader

    def get_for_organization(self, organization_id: UUID) -> OrganizationNotificationSettings:
        email_enabled_raw = self._setting_reader.get_organization_setting_value(
            organization_id,
            EMAIL_ENABLED_KEY,
        )
        email_from_raw = self._setting_reader.get_organization_setting_value(
            organization_id,
            EMAIL_FROM_KEY,
        )
        return OrganizationNotificationSettings(
            email_enabled=_normalize_email_enabled(email_enabled_raw),
            email_from=_normalize_email_from(email_from_raw),
        )


def _normalize_email_enabled(raw: Any | None) -> bool:
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, dict):
        if "enabled" in raw:
            return bool(raw["enabled"])
        if "value" in raw:
            return bool(raw["value"])
    return True


def _normalize_email_from(raw: Any | None) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        normalized = raw.strip()
        return normalized or None
    if isinstance(raw, dict):
        address = raw.get("address") or raw.get("value")
        if isinstance(address, str):
            normalized = address.strip()
            return normalized or None
    return None
