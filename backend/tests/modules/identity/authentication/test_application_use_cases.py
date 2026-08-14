import uuid
from datetime import UTC, datetime

import pytest

from app.modules.identity.application.authentication.client_context import parse_client_context
from app.modules.identity.application.authentication.commands import (
    ClientContextCommand,
    LoginCommand,
    LogoutCommand,
    RefreshSessionCommand,
)
from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.authentication.login import LoginUseCase
from app.modules.identity.application.authentication.logout import LogoutUseCase
from app.modules.identity.application.authentication.policy import TokenPolicy
from app.modules.identity.application.authentication.refresh_session import RefreshSessionUseCase
from app.modules.identity.application.authentication.token_pair_issuer import TokenPairIssuer
from app.modules.identity.domain.authentication.entities.refresh_token import RefreshToken
from app.modules.identity.domain.authentication.entities.session import Session
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.refresh_token_revoke_reason import (
    RefreshTokenRevokeReason,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RevokedRefreshTokenError,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.password_hasher import PasswordHasher
from app.modules.identity.domain.authentication.value_objects.identity.refresh_token_id import RefreshTokenId
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.access_token import (
    AccessToken,
    AccessTokenClaims,
)
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authentication.value_objects.security.password_hash import (
    PasswordHash,
)
from app.modules.identity.domain.authentication.value_objects.security.refresh_token import (
    RefreshToken as RefreshTokenValue,
)
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class SequenceIdGenerator:
    def __init__(self, values: list[uuid.UUID]) -> None:
        self._values = values
        self._index = 0

    def generate_uuid(self) -> uuid.UUID:
        value = self._values[self._index % len(self._values)]
        self._index += 1
        return value


class FakePasswordHasher:
    def hash(self, password: str) -> PasswordHash:
        return PasswordHash(f"hash:{password}")

    def verify(self, password: str, password_hash: PasswordHash) -> bool:
        return password_hash.value == f"hash:{password}"

    def needs_rehash(self, password_hash: PasswordHash) -> bool:
        return False


class FakeTokenService:
    def create_access_token(self, claims: AccessTokenClaims) -> AccessToken:
        return AccessToken.create(f"access:{claims.jti}")

    def decode_access_token(self, token: AccessToken) -> AccessTokenClaims:
        raise NotImplementedError


class FakeRefreshTokenService:
    def __init__(self) -> None:
        self._counter = 0

    def create(self) -> RefreshTokenValue:
        self._counter += 1
        return RefreshTokenValue.create(f"refresh-{self._counter}")

    def hash(self, token: RefreshTokenValue) -> TokenHash:
        return TokenHash(f"hash:{token.value}")

    def verify(self, token: RefreshTokenValue, token_hash: TokenHash) -> bool:
        return token_hash.value == f"hash:{token.value}"


class InMemoryUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users = {user.email.value: user for user in users or []}

    def add(self, user: User) -> User:
        self._users[user.email.value] = user
        return user

    def update(self, user: User) -> User:
        self._users[user.email.value] = user
        return user

    def remove(self, user_id: UserId) -> None:
        self._users = {
            email: user for email, user in self._users.items() if user.id.value != user_id.value
        }

    def get_by_id(self, user_id: UserId) -> User | None:
        for user in self._users.values():
            if user.id.value == user_id.value:
                return user
        return None

    def get_by_email(self, email: Email) -> User | None:
        return self._users.get(email.value)


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[uuid.UUID, Session] = {}

    def add(self, session: Session) -> Session:
        self._sessions[session.id.value] = session
        return session

    def update(self, session: Session) -> Session:
        self._sessions[session.id.value] = session
        return session

    def remove(self, session_id: SessionId) -> None:
        self._sessions.pop(session_id.value, None)

    def get_by_id(self, session_id: SessionId) -> Session | None:
        return self._sessions.get(session_id.value)


class InMemoryRefreshTokenRepository:
    def __init__(self) -> None:
        self._tokens_by_hash: dict[str, RefreshToken] = {}
        self._tokens_by_id: dict[uuid.UUID, RefreshToken] = {}

    def add(self, refresh_token: RefreshToken) -> RefreshToken:
        self._tokens_by_hash[refresh_token.token_hash.value] = refresh_token
        self._tokens_by_id[refresh_token.id.value] = refresh_token
        return refresh_token

    def update(self, refresh_token: RefreshToken) -> RefreshToken:
        self._tokens_by_hash[refresh_token.token_hash.value] = refresh_token
        self._tokens_by_id[refresh_token.id.value] = refresh_token
        return refresh_token

    def remove(self, refresh_token_id: RefreshTokenId) -> None:
        token = self._tokens_by_id.pop(refresh_token_id.value, None)
        if token is not None:
            self._tokens_by_hash.pop(token.token_hash.value, None)

    def get_by_id(self, refresh_token_id: RefreshTokenId) -> RefreshToken | None:
        return self._tokens_by_id.get(refresh_token_id.value)

    def get_by_token_hash(self, token_hash: TokenHash) -> RefreshToken | None:
        return self._tokens_by_hash.get(token_hash.value)

    def get_active_by_session_id(self, session_id: SessionId) -> RefreshToken | None:
        for token in self._tokens_by_id.values():
            if token.session_id.value == session_id.value and token.is_usable(datetime.now(tz=UTC)):
                return token
        return None


def _build_user(status: UserStatus = UserStatus.ACTIVE) -> User:
    now = datetime(2026, 7, 1, tzinfo=UTC)
    return User(
        id=UserId(uuid.UUID("00000000-0000-0000-0000-000000000001")),
        email=Email.create("user@example.com"),
        password_hash=PasswordHash("hash:secret"),
        status=status,
        created_at=now,
        updated_at=now,
    )


def _build_use_cases(user: User | None = None):
    now = datetime(2026, 7, 1, 12, tzinfo=UTC)
    clock = FixedClock(now)
    user_repository = InMemoryUserRepository([user or _build_user()])
    session_repository = InMemorySessionRepository()
    refresh_repository = InMemoryRefreshTokenRepository()
    password_hasher = FakePasswordHasher()
    token_service = FakeTokenService()
    refresh_service = FakeRefreshTokenService()
    id_generator = SequenceIdGenerator(
        [
            uuid.UUID("00000000-0000-0000-0000-000000000010"),
            uuid.UUID("00000000-0000-0000-0000-000000000011"),
            uuid.UUID("00000000-0000-0000-0000-000000000012"),
            uuid.UUID("00000000-0000-0000-0000-000000000013"),
            uuid.UUID("00000000-0000-0000-0000-000000000014"),
        ]
    )
    token_policy = TokenPolicy(access_token_expire_seconds=900, refresh_token_expire_days=30)
    issuer = TokenPairIssuer(
        refresh_token_repository=refresh_repository,
        token_service=token_service,
        refresh_token_service=refresh_service,
        clock=clock,
        token_policy=token_policy,
        id_generator=id_generator,
    )
    login = LoginUseCase(
        user_repository=user_repository,
        session_repository=session_repository,
        password_hasher=password_hasher,
        token_pair_issuer=issuer,
        clock=clock,
        id_generator=id_generator,
    )
    refresh = RefreshSessionUseCase(
        user_repository=user_repository,
        session_repository=session_repository,
        refresh_token_repository=refresh_repository,
        refresh_token_service=refresh_service,
        token_pair_issuer=issuer,
        clock=clock,
    )
    logout = LogoutUseCase(
        session_repository=session_repository,
        refresh_token_repository=refresh_repository,
        refresh_token_service=refresh_service,
        clock=clock,
    )
    return login, refresh, logout, user_repository, session_repository, refresh_repository


def _login_command(password: str = "secret") -> LoginCommand:
    return LoginCommand(
        email="user@example.com",
        password=password,
        client_context=ClientContextCommand(
            ip="127.0.0.1",
            user_agent="pytest",
            device_name="test-device",
        ),
    )


def test_parse_client_context() -> None:
    context = parse_client_context(
        ClientContextCommand(
            ip="127.0.0.1",
            user_agent="pytest",
            device_name="test-device",
        )
    )
    assert context.ip == "127.0.0.1"
    assert context.user_agent == "pytest"
    assert context.device_name == "test-device"


def test_login_success() -> None:
    login, _, _, _, _, _ = _build_use_cases()
    result = login.execute(_login_command())
    assert result.access_token.value.startswith("access:")
    assert result.refresh_token.value.startswith("refresh-")
    assert result.token_type == "bearer"


def test_login_rejects_invalid_password() -> None:
    login, _, _, _, _, _ = _build_use_cases()
    with pytest.raises(InvalidCredentialsError):
        login.execute(_login_command(password="wrong"))


def test_login_rejects_inactive_user() -> None:
    login, _, _, _, _, _ = _build_use_cases(_build_user(UserStatus.SUSPENDED))
    with pytest.raises(InactiveUserError):
        login.execute(_login_command())


def test_refresh_rotates_token() -> None:
    login, refresh, _, _, _, refresh_repository = _build_use_cases()
    login_result = login.execute(_login_command())

    command = RefreshSessionCommand(refresh_token=login_result.refresh_token.value)
    refresh_result = refresh.execute(command)
    assert refresh_result.refresh_token.value != login_result.refresh_token.value

    old = refresh_repository.get_by_token_hash(TokenHash(f"hash:{login_result.refresh_token.value}"))
    assert old is not None
    assert old.revoked_at is not None
    assert old.revoke_reason == RefreshTokenRevokeReason.ROTATED


def test_refresh_rejects_reuse_of_revoked_token() -> None:
    login, refresh, _, _, _, _ = _build_use_cases()
    login_result = login.execute(_login_command())
    command = RefreshSessionCommand(refresh_token=login_result.refresh_token.value)
    refresh.execute(command)

    with pytest.raises(RevokedRefreshTokenError):
        refresh.execute(command)


def test_logout_revokes_session_and_refresh_token() -> None:
    login, _, logout, _, session_repository, refresh_repository = _build_use_cases()
    login_result = login.execute(_login_command())

    logout.execute(LogoutCommand(refresh_token=login_result.refresh_token.value))
    refresh = refresh_repository.get_by_token_hash(TokenHash(f"hash:{login_result.refresh_token.value}"))
    assert refresh is not None
    assert refresh.revoked_at is not None
    assert refresh.revoke_reason == RefreshTokenRevokeReason.LOGOUT
