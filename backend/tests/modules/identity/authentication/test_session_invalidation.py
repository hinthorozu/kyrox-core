import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DbSession, sessionmaker

from app.db.base import Base
from app.modules.identity.application.authentication.revoke_all_user_sessions import (
    RevokeAllUserSessionsUseCase,
)
from app.modules.identity.domain.authentication.entities.refresh_token import RefreshToken
from app.modules.identity.domain.authentication.entities.session import Session as AuthSession
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.refresh_token_revoke_reason import (
    RefreshTokenRevokeReason,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.family_id import FamilyId
from app.modules.identity.domain.authentication.value_objects.identity.refresh_token_id import (
    RefreshTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authentication.value_objects.security.password_hash import (
    PasswordHash,
)
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash
from app.modules.identity.infrastructure.authentication.repositories.sqlalchemy_refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.modules.identity.infrastructure.authentication.repositories.sqlalchemy_session_repository import (
    SqlAlchemySessionRepository,
)
from app.modules.identity.infrastructure.authentication.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


@pytest.fixture
def db_session() -> DbSession:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _build_user(email: str, now: datetime) -> User:
    return User(
        id=UserId(uuid.uuid4()),
        email=Email.create(email),
        password_hash=PasswordHash("hash"),
        status=UserStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def _build_session(
    user_id: UserId,
    now: datetime,
    *,
    revoked_at: datetime | None = None,
) -> AuthSession:
    return AuthSession(
        id=SessionId(uuid.uuid4()),
        user_id=user_id,
        created_at=now,
        updated_at=now,
        revoked_at=revoked_at,
    )


def _build_refresh_token(
    session_id: SessionId,
    token_hash: str,
    now: datetime,
    *,
    expires_at: datetime | None = None,
    used_at: datetime | None = None,
) -> RefreshToken:
    return RefreshToken(
        id=RefreshTokenId(uuid.uuid4()),
        session_id=session_id,
        token_hash=TokenHash(token_hash),
        family_id=FamilyId(uuid.uuid4()),
        expires_at=expires_at or now + timedelta(days=1),
        created_at=now,
        used_at=used_at,
    )


def test_revoke_all_user_sessions_revokes_server_side_credentials_only_for_target_user(
    db_session: DbSession,
) -> None:
    now = datetime(2026, 8, 27, 18, 0, tzinfo=UTC)
    clock = FixedClock(now)
    user_repo = SqlAlchemyUserRepository(db_session, clock)
    session_repo = SqlAlchemySessionRepository(db_session)
    refresh_repo = SqlAlchemyRefreshTokenRepository(db_session, clock)

    target_user = user_repo.add(_build_user("target@example.com", now))
    other_user = user_repo.add(_build_user("other@example.com", now))

    target_session_one = session_repo.add(_build_session(target_user.id, now))
    target_session_two = session_repo.add(_build_session(target_user.id, now))
    already_revoked_target_session = session_repo.add(
        _build_session(
            target_user.id,
            now,
            revoked_at=now - timedelta(minutes=5),
        )
    )
    other_session = session_repo.add(_build_session(other_user.id, now))

    target_active_token = refresh_repo.add(
        _build_refresh_token(target_session_one.id, "target-active", now)
    )
    target_token_on_revoked_session = refresh_repo.add(
        _build_refresh_token(
            already_revoked_target_session.id,
            "target-active-on-revoked-session",
            now,
        )
    )
    target_used_token = refresh_repo.add(
        _build_refresh_token(
            target_session_two.id,
            "target-used",
            now,
            used_at=now - timedelta(minutes=1),
        )
    )
    target_expired_token = refresh_repo.add(
        _build_refresh_token(
            target_session_two.id,
            "target-expired",
            now,
            expires_at=now - timedelta(minutes=1),
        )
    )
    other_active_token = refresh_repo.add(
        _build_refresh_token(other_session.id, "other-active", now)
    )
    db_session.commit()

    active_session_ids = {
        session.id.value for session in session_repo.get_active_by_user_id(target_user.id)
    }
    assert active_session_ids == {
        target_session_one.id.value,
        target_session_two.id.value,
    }

    active_target_hashes = {
        token.token_hash.value for token in refresh_repo.get_active_by_user_id(target_user.id)
    }
    assert active_target_hashes == {
        "target-active",
        "target-active-on-revoked-session",
    }

    use_case = RevokeAllUserSessionsUseCase(
        session_repository=session_repo,
        refresh_token_repository=refresh_repo,
        clock=clock,
    )
    result = use_case.execute(target_user.id)
    db_session.commit()

    assert result.sessions_revoked == 2
    assert result.refresh_tokens_revoked == 2

    assert session_repo.get_by_id(target_session_one.id).is_active is False
    assert session_repo.get_by_id(target_session_two.id).is_active is False
    assert session_repo.get_by_id(other_session.id).is_active is True

    reloaded_target_active = refresh_repo.get_by_id(target_active_token.id)
    assert reloaded_target_active is not None
    assert reloaded_target_active.revoked_reason is RefreshTokenRevokeReason.SESSION_REVOKED

    reloaded_inconsistent = refresh_repo.get_by_id(target_token_on_revoked_session.id)
    assert reloaded_inconsistent is not None
    assert reloaded_inconsistent.revoked_reason is RefreshTokenRevokeReason.SESSION_REVOKED

    reloaded_used = refresh_repo.get_by_id(target_used_token.id)
    assert reloaded_used is not None
    assert reloaded_used.revoked_at is None

    reloaded_expired = refresh_repo.get_by_id(target_expired_token.id)
    assert reloaded_expired is not None
    assert reloaded_expired.revoked_at is None

    reloaded_other = refresh_repo.get_by_id(other_active_token.id)
    assert reloaded_other is not None
    assert reloaded_other.revoked_at is None
    assert session_repo.get_active_by_user_id(other_user.id)[0].id == other_session.id

    second_result = use_case.execute(target_user.id)
    assert second_result.sessions_revoked == 0
    assert second_result.refresh_tokens_revoked == 0
