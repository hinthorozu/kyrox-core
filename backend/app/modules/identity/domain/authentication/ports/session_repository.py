from typing import Protocol
from uuid import UUID

from app.modules.identity.domain.authentication.entities.session import Session
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId


class SessionRepository(Protocol):
    def add(self, session: Session) -> Session: ...

    def update(self, session: Session) -> Session: ...

    def remove(self, session_id: SessionId) -> None: ...

    def get_by_id(self, session_id: SessionId) -> Session | None: ...

    def get_active_by_user_id(self, user_id: UserId) -> list[Session]: ...

    def get_active_by_organization_id(self, organization_id: UUID) -> list[Session]: ...
