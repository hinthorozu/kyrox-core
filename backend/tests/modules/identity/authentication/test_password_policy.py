import pytest

from app.modules.identity.application.authentication.password_policy import (
    PasswordPolicy,
    PasswordPolicyViolation,
)


def test_password_policy_accepts_minimum_length_without_composition_requirements() -> None:
    PasswordPolicy().validate("aaaaaaaaaaaa")


def test_password_policy_accepts_maximum_length() -> None:
    PasswordPolicy().validate("a" * 255)


def test_password_policy_accepts_unicode_passwords() -> None:
    PasswordPolicy().validate("şifre-güçlü-123")


def test_password_policy_rejects_too_short_password() -> None:
    with pytest.raises(PasswordPolicyViolation, match="at least 12 characters"):
        PasswordPolicy().validate("a" * 11)


def test_password_policy_rejects_too_long_password() -> None:
    with pytest.raises(PasswordPolicyViolation, match="at most 255 characters"):
        PasswordPolicy().validate("a" * 256)


def test_password_policy_error_never_echoes_password() -> None:
    raw_password = "secret"

    with pytest.raises(PasswordPolicyViolation) as exc_info:
        PasswordPolicy().validate(raw_password)

    assert raw_password not in str(exc_info.value)
