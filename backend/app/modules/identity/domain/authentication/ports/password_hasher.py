from typing import Protocol

from app.modules.identity.domain.authentication.value_objects.security.password_hash import (
    PasswordHash,
)


class PasswordHasher(Protocol):
    def hash(self, password: str) -> PasswordHash: ...

    def verify(self, password: str, password_hash: PasswordHash) -> bool: ...

    def needs_rehash(self, password_hash: PasswordHash) -> bool: ...
