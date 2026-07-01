import pytest

from app.modules.settings.application.policy import SettingPolicy
from app.modules.settings.domain.exceptions import (
    InvalidSettingKeyError,
    InvalidSettingScopeError,
    InvalidSettingValueError,
)
from app.modules.settings.domain.value_objects.setting_scope import SettingScope


def test_policy_rejects_null_value() -> None:
    policy = SettingPolicy()
    with pytest.raises(InvalidSettingValueError):
        policy.validate_value(None)


def test_policy_accepts_empty_object() -> None:
    policy = SettingPolicy()
    assert policy.validate_value({}) == {}


def test_policy_rejects_oversized_value() -> None:
    policy = SettingPolicy(max_value_bytes=16)
    with pytest.raises(InvalidSettingValueError):
        policy.validate_value({"payload": "x" * 32})


def test_policy_validates_organization_scope_requires_org_id() -> None:
    policy = SettingPolicy()
    with pytest.raises(InvalidSettingScopeError):
        policy.validate_scope(SettingScope.ORGANIZATION, None)


def test_policy_validates_system_scope_requires_null_org_id() -> None:
    policy = SettingPolicy()
    import uuid

    with pytest.raises(InvalidSettingScopeError):
        policy.validate_scope(SettingScope.SYSTEM, uuid.uuid4())


def test_policy_rejects_short_key_prefix() -> None:
    policy = SettingPolicy()
    with pytest.raises(InvalidSettingKeyError):
        policy.validate_key_prefix("ab")
