import logging
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.identity.application.authentication.identity_action_tokens import (
    ConsumeIdentityActionToken,
    IssueIdentityActionToken,
)
from app.modules.identity.domain.authentication.entities.identity_action_token import (
    IdentityActionToken,
)
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.exceptions.identity_action_token import (
    IdentityActionTokenConsumedError,
    IdentityActionTokenExpiredError,
    IdentityActionTokenNotFoundError,
    IdentityActionTokenPurposeMismatchError,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


class SequenceIdGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def generate_uuid(self) -> uuid.UUID:
        self._counter += 1
        return uuid.UUID(int=self._counter)


class FakeIdentityActionTokenService:
    def __init__(self, raw_tokens: list[str]) -> None:
        self._raw_tokens = raw_tokens
        self._index = 0

    def generate(self) -> str:
        raw_token = self._raw_tokens[self._index]
        self._index += 1
        return raw_token

    def hash(self, raw_token: str) -> TokenHash:
        return TokenHash(f"hash:{raw_token}")


class InMemoryIdentityActionTokenRepository:
    def __init__(self) -> None:
        self.tokens: dict[str, IdentityActionToken] = {}

    def add(self, token: IdentityActionToken) -> IdentityActionToken:
        self.tokens[token.token_hash.value] = token
        return token

    def update(self, token: IdentityActionToken) -> IdentityActionToken:
        self.tokens[token.token_hash.value] = token
        return token

    def get_by_token_hash(self, token_hash: TokenHash) -> IdentityActionToken | None:
        return self.tokens.get(token_hash.value)

    def consume_if_available(
        self,
        token_hash: TokenHash,
        purpose: IdentityActionTokenPurpose,
        consumed_at: datetime,
    ) -> IdentityActionToken | None:
        token = self.tokens.get(token_hash.value)
        if token is None or token.purpose is not purpose or not token.is_available(consumed_at):
            return None
        token.consume(consumed_at, purpose)
        return token

    def invalidate_outstanding_for_user_purpose(
        self,
        user_id: UserId,
        purpose: IdentityActionTokenPurpose,
        invalidated_at: datetime,
    ) -> int:
        count = 0
        for token in self.tokens.values():
            if (
                token.user_id == user_id
                and token.purpose is purpose
                and token.consumed_at is None
                and token.invalidated_at is None
            ):
                token.invalidate(invalidated_at)
                count += 1
        return count


def _build_use_cases(
    raw_tokens: list[str] | None = None,
) -> tuple[
    IssueIdentityActionToken,
    ConsumeIdentityActionToken,
    MutableClock,
    InMemoryIdentityActionTokenRepository,
]:
    clock = MutableClock(datetime(2026, 8, 27, 12, 0, tzinfo=UTC))
    repository = InMemoryIdentityActionTokenRepository()
    token_service = FakeIdentityActionTokenService(raw_tokens or ["secret-token"])
    issue = IssueIdentityActionToken(
        repository=repository,
        token_service=token_service,
        clock=clock,
        id_generator=SequenceIdGenerator(),
    )
    consume = ConsumeIdentityActionToken(
        repository=repository,
        token_service=token_service,
        clock=clock,
    )
    return issue, consume, clock, repository


def test_issue_returns_raw_token_but_persists_only_hash() -> None:
    issue, _consume, _clock, repository = _build_use_cases(["activation-secret"])
    user_id = UserId(uuid.UUID("00000000-0000-0000-0000-000000000111"))

    result = issue.execute(
        user_id,
        IdentityActionTokenPurpose.ACCOUNT_ACTIVATION,
        timedelta(hours=24),
    )

    assert result.raw_token == "activation-secret"
    assert "activation-secret" not in repository.tokens
    persisted = repository.tokens["hash:activation-secret"]
    assert persisted.token_hash.value == "hash:activation-secret"
    assert not hasattr(persisted, "raw_token")


def test_reissue_supersedes_older_token_for_same_user_and_purpose() -> None:
    issue, _consume, clock, repository = _build_use_cases(["first", "second"])
    user_id = UserId(uuid.UUID("00000000-0000-0000-0000-000000000222"))

    issue.execute(user_id, IdentityActionTokenPurpose.PASSWORD_RESET, timedelta(hours=1))
    first = repository.tokens["hash:first"]
    clock.advance(timedelta(minutes=5))
    issue.execute(user_id, IdentityActionTokenPurpose.PASSWORD_RESET, timedelta(hours=1))

    assert first.invalidated_at == clock.now()
    assert repository.tokens["hash:second"].invalidated_at is None


def test_expired_token_is_rejected_deterministically() -> None:
    issue, consume, clock, _repository = _build_use_cases(["expiring"])
    user_id = UserId(uuid.UUID("00000000-0000-0000-0000-000000000333"))
    issue.execute(user_id, IdentityActionTokenPurpose.PASSWORD_RESET, timedelta(minutes=10))
    clock.advance(timedelta(minutes=10))

    with pytest.raises(IdentityActionTokenExpiredError):
        consume.execute("expiring", IdentityActionTokenPurpose.PASSWORD_RESET)


def test_replay_is_rejected_after_first_successful_consume() -> None:
    issue, consume, _clock, _repository = _build_use_cases(["single-use"])
    user_id = UserId(uuid.UUID("00000000-0000-0000-0000-000000000444"))
    issue.execute(user_id, IdentityActionTokenPurpose.PASSWORD_RESET, timedelta(hours=1))

    assert consume.execute("single-use", IdentityActionTokenPurpose.PASSWORD_RESET) == user_id
    with pytest.raises(IdentityActionTokenConsumedError):
        consume.execute("single-use", IdentityActionTokenPurpose.PASSWORD_RESET)


def test_wrong_purpose_is_rejected_without_consuming_token() -> None:
    issue, consume, _clock, repository = _build_use_cases(["wrong-purpose"])
    user_id = UserId(uuid.UUID("00000000-0000-0000-0000-000000000555"))
    issue.execute(user_id, IdentityActionTokenPurpose.PASSWORD_RESET, timedelta(hours=1))

    with pytest.raises(IdentityActionTokenPurposeMismatchError):
        consume.execute("wrong-purpose", IdentityActionTokenPurpose.ACCOUNT_ACTIVATION)

    assert repository.tokens["hash:wrong-purpose"].consumed_at is None


def test_unknown_token_is_rejected() -> None:
    _issue, consume, _clock, _repository = _build_use_cases(["unused"])

    with pytest.raises(IdentityActionTokenNotFoundError):
        consume.execute("missing", IdentityActionTokenPurpose.PASSWORD_RESET)


def test_raw_token_is_not_logged_by_issue_or_consume(caplog: pytest.LogCaptureFixture) -> None:
    issue, consume, _clock, _repository = _build_use_cases(["never-log-this-secret"])
    user_id = UserId(uuid.UUID("00000000-0000-0000-0000-000000000666"))

    with caplog.at_level(logging.DEBUG):
        issue.execute(user_id, IdentityActionTokenPurpose.PASSWORD_RESET, timedelta(hours=1))
        consume.execute("never-log-this-secret", IdentityActionTokenPurpose.PASSWORD_RESET)

    assert "never-log-this-secret" not in caplog.text
