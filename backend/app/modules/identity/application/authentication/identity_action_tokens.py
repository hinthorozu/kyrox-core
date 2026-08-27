from dataclasses import dataclass
from datetime import timedelta

from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.domain.authentication.entities.identity_action_token import (
    IdentityActionToken,
)
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.exceptions.identity_action_token import (
    IdentityActionTokenConsumedError,
    IdentityActionTokenNotFoundError,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.identity_action_token_repository import (
    IdentityActionTokenRepository,
)
from app.modules.identity.domain.authentication.ports.identity_action_token_service import (
    IdentityActionTokenService,
)
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId


@dataclass(frozen=True, slots=True)
class IssuedIdentityActionToken:
    raw_token: str
    expires_at: object


class IssueIdentityActionToken:
    def __init__(
        self,
        repository: IdentityActionTokenRepository,
        token_service: IdentityActionTokenService,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._repository = repository
        self._token_service = token_service
        self._clock = clock
        self._id_generator = id_generator

    def execute(
        self,
        user_id: UserId,
        purpose: IdentityActionTokenPurpose,
        ttl: timedelta,
    ) -> IssuedIdentityActionToken:
        if ttl <= timedelta(0):
            raise ValueError("Identity action token TTL must be positive")

        now = self._clock.now()
        raw_token = self._token_service.generate()
        token_hash = self._token_service.hash(raw_token)
        expires_at = now + ttl

        self._repository.invalidate_outstanding_for_user_purpose(
            user_id,
            purpose,
            now,
        )
        token = IdentityActionToken(
            id=IdentityActionTokenId(self._id_generator.generate_uuid()),
            user_id=user_id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=now,
        )
        self._repository.add(token)
        return IssuedIdentityActionToken(raw_token=raw_token, expires_at=expires_at)


class ConsumeIdentityActionToken:
    def __init__(
        self,
        repository: IdentityActionTokenRepository,
        token_service: IdentityActionTokenService,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._token_service = token_service
        self._clock = clock

    def execute(
        self,
        raw_token: str,
        expected_purpose: IdentityActionTokenPurpose,
    ) -> UserId:
        token_hash = self._token_service.hash(raw_token)
        now = self._clock.now()
        consumed = self._repository.consume_if_available(
            token_hash,
            expected_purpose,
            now,
        )
        if consumed is not None:
            return consumed.user_id

        token = self._repository.get_by_token_hash(token_hash)
        if token is None:
            raise IdentityActionTokenNotFoundError("Identity action token not found")

        token.consume(now, expected_purpose)
        raise IdentityActionTokenConsumedError("Identity action token could not be consumed")
