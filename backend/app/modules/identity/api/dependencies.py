from fastapi import Depends
from sqlalchemy.orm import Session as DbSession

from app.db.session import get_db
from app.modules.identity.application.auth import (
    LoginUseCase,
    LogoutUseCase,
    RefreshSessionUseCase,
)
from app.modules.identity.infrastructure.repositories import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.security.argon2_password_hasher import (
    Argon2idPasswordHasher,
)
from app.modules.identity.infrastructure.security.jwt_token_service import JwtTokenService
from app.modules.identity.infrastructure.security.refresh_token_service import (
    SecureRefreshTokenService,
)


def get_login_use_case(db: DbSession = Depends(get_db)) -> LoginUseCase:
    return LoginUseCase(
        user_repository=SqlAlchemyUserRepository(db),
        session_repository=SqlAlchemySessionRepository(db),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db),
        password_hasher=Argon2idPasswordHasher(),
        token_service=JwtTokenService(),
        refresh_token_service=SecureRefreshTokenService(),
    )


def get_refresh_session_use_case(db: DbSession = Depends(get_db)) -> RefreshSessionUseCase:
    return RefreshSessionUseCase(
        user_repository=SqlAlchemyUserRepository(db),
        session_repository=SqlAlchemySessionRepository(db),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db),
        token_service=JwtTokenService(),
        refresh_token_service=SecureRefreshTokenService(),
    )


def get_logout_use_case(db: DbSession = Depends(get_db)) -> LogoutUseCase:
    return LogoutUseCase(
        session_repository=SqlAlchemySessionRepository(db),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(db),
        refresh_token_service=SecureRefreshTokenService(),
    )
