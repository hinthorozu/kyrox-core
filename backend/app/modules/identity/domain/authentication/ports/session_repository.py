from typing import Protocol

from app.modules.identity.domain.authentication.entities.session import Session
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId


class SessionRepository(Protocol):
    def add(self, session: Session) -> Session: ...

    def update(self, session: Session) -> Session: ...

    def remove(self, session_id: SessionId) -> None: ...

    def get_by_id(self, session_id: SessionId) -> Session | None: ...
