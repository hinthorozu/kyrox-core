import uuid

import pytest

from app.modules.identity.domain.membership.value_objects import (
    InviteEmail,
    InviteId,
    InviteTokenHash,
    MembershipId,
)


def test_invite_email_create() -> None:
    email = InviteEmail.create("Member@Example.com")
    assert email.value == "member@example.com"


def test_invite_email_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        InviteEmail.create("not-an-email")


def test_membership_and_invite_ids_require_uuid() -> None:
    value = uuid.uuid4()
    assert MembershipId(value).value == value
    assert InviteId(value).value == value


def test_invite_token_hash_requires_non_empty_value() -> None:
    token_hash = InviteTokenHash("hash-value")
    assert token_hash.value == "hash-value"

    with pytest.raises(ValueError):
        InviteTokenHash("")
