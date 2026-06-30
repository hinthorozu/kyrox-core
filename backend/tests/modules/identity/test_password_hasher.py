import uuid
from datetime import UTC, datetime

import pytest
from app.modules.identity.infrastructure.security.argon2_password_hasher import (
    Argon2idPasswordHasher,
)


def test_password_hasher_hashes_and_verifies_password() -> None:
    hasher = Argon2idPasswordHasher()
    password = "correct-horse-battery-staple"
    password_hash = hasher.hash(password)

    assert password_hash != password
    assert hasher.verify(password, password_hash) is True


def test_password_hasher_rejects_wrong_password() -> None:
    hasher = Argon2idPasswordHasher()
    password_hash = hasher.hash("secret-password")

    assert hasher.verify("wrong-password", password_hash) is False
