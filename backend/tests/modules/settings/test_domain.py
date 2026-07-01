import pytest

from app.modules.settings.domain.exceptions import InvalidSettingKeyError
from app.modules.settings.domain.value_objects.setting_key import SettingKey
from app.modules.settings.domain.value_objects.setting_scope import SettingScope


def test_setting_key_accepts_valid_namespaced_key() -> None:
    key = SettingKey.create("fair_crm.pipeline.default_stage")
    assert key.value == "fair_crm.pipeline.default_stage"


def test_setting_key_normalizes_to_lowercase() -> None:
    key = SettingKey.create(" FAIR_CRM.Pipeline.Default_Stage ")
    assert key.value == "fair_crm.pipeline.default_stage"


def test_setting_key_rejects_too_few_segments() -> None:
    with pytest.raises(InvalidSettingKeyError):
        SettingKey.create("feature.only")


def test_setting_scope_values() -> None:
    assert SettingScope.SYSTEM.value == "system"
    assert SettingScope.ORGANIZATION.value == "organization"
