from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authentication.entities.session import Session
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.infrastructure.authentication.persistence.mappers.session_mapper import (
    SessionMapper,
)
from app.modules.identity.infrastructure.authentication.persistence.models.session import SessionModel
from app.modules.identity.infrastructure.persistence.models import UserModel


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

    def get_active_by_user_id(self, user_id: UserId) -> list[Session]:
        stmt = (
            select(SessionModel)
            .where(
                SessionModel.user_id == user_id.value,
                SessionModel.revoked_at.is_(None),
            )
            .order_by(SessionModel.created_at.asc())
        )
        return [SessionMapper.to_domain(model) for model in self._session.scalars(stmt).all()]

    def get_active_by_organization_id(self, organization_id: UUID) -> list[Session]:
        stmt = (
            select(SessionModel)
            .join(UserModel, UserModel.id == SessionModel.user_id)
            .where(
                UserModel.organization_id == organization_id,
                UserModel.is_super_admin.is_(False),
                UserModel.deleted_at.is_(None),
                SessionModel.revoked_at.is_(None),
            )
            .order_by(SessionModel.created_at.asc())
        )
        return [SessionMapper.to_domain(model) for model in self._session.scalars(stmt).all()]
