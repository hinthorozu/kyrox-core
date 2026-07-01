from typing import Protocol

from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email


class UserRepository(Protocol):
    def add(self, user: User) -> User: ...

    def update(self, user: User) -> User: ...

    def remove(self, user_id: UserId) -> None: ...

    def get_by_id(self, user_id: UserId) -> User | None: ...

    def get_by_email(self, email: Email) -> User | None: ...
