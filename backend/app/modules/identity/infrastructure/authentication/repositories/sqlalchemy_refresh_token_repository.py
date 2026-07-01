from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authentication.entities.refresh_token import RefreshToken
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.value_objects.identity.refresh_token_id import (
    RefreshTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash
from app.modules.identity.infrastructure.authentication.persistence.mappers.refresh_token_mapper import (
    RefreshTokenMapper,
)
from app.modules.identity.infrastructure.authentication.persistence.models.refresh_token import (
    RefreshTokenModel,
)


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: DbSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def add(self, refresh_token: RefreshToken) -> RefreshToken:
        model = RefreshTokenMapper.to_model(refresh_token)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return RefreshTokenMapper.to_domain(model)

    def update(self, refresh_token: RefreshToken) -> RefreshToken:
        model = self._session.get(RefreshTokenModel, refresh_token.id.value)
        if model is None:
            raise ValueError(f"Refresh token not found: {refresh_token.id.value}")

        RefreshTokenMapper.apply_to_model(refresh_token, model)
        self._session.flush()
        self._session.refresh(model)
        return RefreshTokenMapper.to_domain(model)

    def remove(self, refresh_token_id: RefreshTokenId) -> None:
        model = self._session.get(RefreshTokenModel, refresh_token_id.value)
        if model is None:
            raise ValueError(f"Refresh token not found: {refresh_token_id.value}")

        self._session.delete(model)
        self._session.flush()

    def get_by_id(self, refresh_token_id: RefreshTokenId) -> RefreshToken | None:
        model = self._session.get(RefreshTokenModel, refresh_token_id.value)
        if model is None:
            return None
        return RefreshTokenMapper.to_domain(model)

    def get_by_token_hash(self, token_hash: TokenHash) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash.value)
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return RefreshTokenMapper.to_domain(model)

    def get_active_by_session_id(self, session_id: SessionId) -> RefreshToken | None:
        now = self._clock.now()
        stmt = (
            select(RefreshTokenModel)
            .where(
                RefreshTokenModel.session_id == session_id.value,
                RefreshTokenModel.revoked_at.is_(None),
                RefreshTokenModel.used_at.is_(None),
                RefreshTokenModel.expires_at > now,
            )
            .order_by(RefreshTokenModel.created_at.desc())
            .limit(1)
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return RefreshTokenMapper.to_domain(model)
