import pytest

from app.modules.jobs.application.policy import JobPolicy
from app.modules.jobs.domain.exceptions import InvalidJobPayloadError


def test_policy_requires_object_payload() -> None:
    policy = JobPolicy()
    with pytest.raises(InvalidJobPayloadError):
        policy.validate_payload(["not", "an", "object"])


def test_policy_normalizes_max_attempts() -> None:
    policy = JobPolicy()
    assert policy.normalize_max_attempts(None) == 3
    assert policy.normalize_max_attempts(1) == 1


def test_policy_rejects_invalid_idempotency_key() -> None:
    policy = JobPolicy()
    with pytest.raises(InvalidJobPayloadError):
        policy.normalize_idempotency_key("bad key!")
