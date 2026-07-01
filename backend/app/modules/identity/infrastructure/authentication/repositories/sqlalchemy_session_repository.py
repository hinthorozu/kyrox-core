from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authentication.entities.session import Session
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.infrastructure.authentication.persistence.mappers.session_mapper import (
    SessionMapper,
)
from app.modules.identity.infrastructure.authentication.persistence.models.session import SessionModel


class SqlAlchemySessionRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def add(self, session: Session) -> Session:
        model = SessionMapper.to_model(session)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return SessionMapper.to_domain(model)

    def update(self, session: Session) -> Session:
        model = self._session.get(SessionModel, session.id.value)
        if model is None:
            raise ValueError(f"Session not found: {session.id.value}")

        SessionMapper.apply_to_model(session, model)
        self._session.flush()
        self._session.refresh(model)
        return SessionMapper.to_domain(model)

    def remove(self, session_id: SessionId) -> None:
        model = self._session.get(SessionModel, session_id.value)
        if model is None:
            raise ValueError(f"Session not found: {session_id.value}")

        self._session.delete(model)
        self._session.flush()

    def get_by_id(self, session_id: SessionId) -> Session | None:
        model = self._session.get(SessionModel, session_id.value)
        if model is None:
            return None
        return SessionMapper.to_domain(model)
