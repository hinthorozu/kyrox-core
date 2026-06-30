import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.modules.identity.application.auth import LoginUseCase, LogoutUseCase, RefreshSessionUseCase
from app.modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401
from app.modules.identity.domain.entities import User
from app.modules.identity.domain.enums import UserStatus
from app.modules.identity.domain.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.modules.identity.infrastructure.repositories import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.security.argon2_password_hasher import Argon2idPasswordHasher
from app.modules.identity.infrastructure.security.jwt_token_service import JwtTokenService
from app.modules.identity.infrastructure.security.refresh_token_service import SecureRefreshTokenService


def _refresh_token_service() -> SecureRefreshTokenService:
    return SecureRefreshTokenService()


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def _seed_active_user(db_session: Session, email: str, password: str) -> User:
    hasher = Argon2idPasswordHasher()
    user_repo = SqlAlchemyUserRepository(db_session)
    return user_repo.create(
        User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hasher.hash(password),
            status=UserStatus.ACTIVE,
            is_super_admin=False,
            created_at=_now(),
            updated_at=_now(),
        )
    )


def test_login_success(db_session: Session) -> None:
    _seed_active_user(db_session, "user@example.com", "password123")
    db_session.commit()

    use_case = LoginUseCase(
        user_repository=SqlAlchemyUserRepository(db_session),
        session_repository=SqlAlchemySessionRepository(db_session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session),
        password_hasher=Argon2idPasswordHasher(),
        token_service=JwtTokenService(),
        refresh_token_service=_refresh_token_service(),
    )

    token_pair = use_case.execute(email="  User@Example.com ", password="password123")
    db_session.commit()

    assert token_pair.token_type == "bearer"
    assert token_pair.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert token_pair.access_token
    assert token_pair.refresh_token


def test_login_rejects_invalid_password(db_session: Session) -> None:
    _seed_active_user(db_session, "user@example.com", "password123")
    db_session.commit()

    use_case = LoginUseCase(
        user_repository=SqlAlchemyUserRepository(db_session),
        session_repository=SqlAlchemySessionRepository(db_session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session),
        password_hasher=Argon2idPasswordHasher(),
        token_service=JwtTokenService(),
        refresh_token_service=_refresh_token_service(),
    )

    with pytest.raises(InvalidCredentialsError):
        use_case.execute(email="user@example.com", password="wrong")


def test_login_rejects_inactive_user(db_session: Session) -> None:
    hasher = Argon2idPasswordHasher()
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.create(
        User(
            id=uuid.uuid4(),
            email="inactive@example.com",
            password_hash=hasher.hash("password123"),
            status=UserStatus.SUSPENDED,
            is_super_admin=False,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    db_session.commit()

    use_case = LoginUseCase(
        user_repository=SqlAlchemyUserRepository(db_session),
        session_repository=SqlAlchemySessionRepository(db_session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session),
        password_hasher=Argon2idPasswordHasher(),
        token_service=JwtTokenService(),
        refresh_token_service=_refresh_token_service(),
    )

    with pytest.raises(InactiveUserError):
        use_case.execute(email="inactive@example.com", password="password123")


def test_refresh_success(db_session: Session) -> None:
    _seed_active_user(db_session, "user@example.com", "password123")
    db_session.commit()

    login_use_case = LoginUseCase(
        user_repository=SqlAlchemyUserRepository(db_session),
        session_repository=SqlAlchemySessionRepository(db_session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session),
        password_hasher=Argon2idPasswordHasher(),
        token_service=JwtTokenService(),
        refresh_token_service=_refresh_token_service(),
    )
    initial_pair = login_use_case.execute(email="user@example.com", password="password123")
    db_session.commit()

    refresh_use_case = RefreshSessionUseCase(
        user_repository=SqlAlchemyUserRepository(db_session),
        session_repository=SqlAlchemySessionRepository(db_session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session),
        token_service=JwtTokenService(),
        refresh_token_service=_refresh_token_service(),
    )
    refreshed_pair = refresh_use_case.execute(refresh_token=initial_pair.refresh_token)
    db_session.commit()

    assert refreshed_pair.access_token != initial_pair.access_token
    assert refreshed_pair.refresh_token != initial_pair.refresh_token


def test_refresh_rejects_invalid_token(db_session: Session) -> None:
    refresh_use_case = RefreshSessionUseCase(
        user_repository=SqlAlchemyUserRepository(db_session),
        session_repository=SqlAlchemySessionRepository(db_session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session),
        token_service=JwtTokenService(),
        refresh_token_service=_refresh_token_service(),
    )

    with pytest.raises(InvalidRefreshTokenError):
        refresh_use_case.execute(refresh_token="not-a-valid-token")


def test_logout_revokes_session_and_refresh_token(db_session: Session) -> None:
    _seed_active_user(db_session, "user@example.com", "password123")
    db_session.commit()

    login_use_case = LoginUseCase(
        user_repository=SqlAlchemyUserRepository(db_session),
        session_repository=SqlAlchemySessionRepository(db_session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session),
        password_hasher=Argon2idPasswordHasher(),
        token_service=JwtTokenService(),
        refresh_token_service=_refresh_token_service(),
    )
    token_pair = login_use_case.execute(email="user@example.com", password="password123")
    db_session.commit()

    logout_use_case = LogoutUseCase(
        session_repository=SqlAlchemySessionRepository(db_session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session),
        refresh_token_service=_refresh_token_service(),
    )
    logout_use_case.execute(refresh_token=token_pair.refresh_token)
    db_session.commit()

    refresh_use_case = RefreshSessionUseCase(
        user_repository=SqlAlchemyUserRepository(db_session),
        session_repository=SqlAlchemySessionRepository(db_session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db_session),
        token_service=JwtTokenService(),
        refresh_token_service=_refresh_token_service(),
    )

    with pytest.raises(InvalidRefreshTokenError):
        refresh_use_case.execute(refresh_token=token_pair.refresh_token)
