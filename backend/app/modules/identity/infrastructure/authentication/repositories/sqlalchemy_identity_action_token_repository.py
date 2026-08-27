from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authentication.entities.identity_action_token import (
    IdentityActionToken,
)
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash
from app.modules.identity.infrastructure.authentication.persistence.mappers.identity_action_token_mapper import (
    IdentityActionTokenMapper,
)
from app.modules.identity.infrastructure.authentication.persistence.models.identity_action_token import (
    IdentityActionTokenModel,
)


class SqlAlchemyIdentityActionTokenRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def add(self, token: IdentityActionToken) -> IdentityActionToken:
        model = IdentityActionTokenMapper.to_model(token)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return IdentityActionTokenMapper.to_domain(model)

    def update(self, token: IdentityActionToken) -> IdentityActionToken:
        model = self._session.get(IdentityActionTokenModel, token.id.value)
        if model is None:
            raise ValueError(f"Identity action token not found: {token.id.value}")

        IdentityActionTokenMapper.apply_to_model(token, model)
        self._session.flush()
        self._session.refresh(model)
        return IdentityActionTokenMapper.to_domain(model)

    def get_by_id(self, token_id: IdentityActionTokenId) -> IdentityActionToken | None:
        model = self._session.get(IdentityActionTokenModel, token_id.value)
        if model is None:
            return None
        return IdentityActionTokenMapper.to_domain(model)

    def get_by_token_hash(self, token_hash: TokenHash) -> IdentityActionToken | None:
        stmt = select(IdentityActionTokenModel).where(
            IdentityActionTokenModel.token_hash == token_hash.value
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return IdentityActionTokenMapper.to_domain(model)

    def consume_if_available(
        self,
        token_hash: TokenHash,
        purpose: IdentityActionTokenPurpose,
        consumed_at: datetime,
    ) -> IdentityActionToken | None:
        stmt = (
            update(IdentityActionTokenModel)
            .where(
                IdentityActionTokenModel.token_hash == token_hash.value,
                IdentityActionTokenModel.purpose == purpose.value,
                IdentityActionTokenModel.consumed_at.is_(None),
                IdentityActionTokenModel.invalidated_at.is_(None),
                IdentityActionTokenModel.expires_at > consumed_at,
            )
            .values(consumed_at=consumed_at)
        )
        result = self._session.execute(stmt)
        if result.rowcount != 1:
            return None
        self._session.flush()
        return self.get_by_token_hash(token_hash)

    def invalidate_outstanding_for_user_purpose(
        self,
        user_id: UserId,
        purpose: IdentityActionTokenPurpose,
        invalidated_at: datetime,
    ) -> int:
        stmt = (
            update(IdentityActionTokenModel)
            .where(
                IdentityActionTokenModel.user_id == user_id.value,
                IdentityActionTokenModel.purpose == purpose.value,
                IdentityActionTokenModel.consumed_at.is_(None),
                IdentityActionTokenModel.invalidated_at.is_(None),
            )
            .values(invalidated_at=invalidated_at)
        )
        result = self._session.execute(stmt)
        self._session.flush()
        return int(result.rowcount or 0)
