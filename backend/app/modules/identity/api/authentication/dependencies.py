from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.db.session import get_db
from app.modules.identity.application.authentication.id_generator import IdGenerator, Uuid4IdGenerator
from app.modules.identity.application.authentication.login import LoginUseCase
from app.modules.identity.application.authentication.logout import LogoutUseCase
from app.modules.identity.application.authentication.policy import TokenPolicy
from app.modules.identity.application.authentication.refresh_session import RefreshSessionUseCase
from app.modules.identity.application.authentication.token_pair_issuer import TokenPairIssuer
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.password_hasher import PasswordHasher
from app.modules.identity.domain.authentication.ports.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.modules.identity.domain.authentication.ports.refresh_token_service import RefreshTokenService
from app.modules.identity.domain.authentication.ports.session_repository import SessionRepository
from app.modules.identity.domain.authentication.ports.token_service import TokenService
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.infrastructure.authentication.clock import UtcClock
from app.modules.identity.infrastructure.authentication.repositories import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.authentication.security import (
    Argon2idPasswordHasher,
    JwtTokenService,
    RefreshTokenService as RefreshTokenServiceImpl,
)


@lru_cache
def get_clock() -> Clock:
    return UtcClock()


@lru_cache
def get_password_hasher() -> PasswordHasher:
    return Argon2idPasswordHasher()


@lru_cache
def get_token_service() -> TokenService:
    return JwtTokenService(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


@lru_cache
def get_refresh_token_service() -> RefreshTokenService:
    return RefreshTokenServiceImpl()


def get_id_generator() -> IdGenerator:
    return Uuid4IdGenerator()


def get_token_policy() -> TokenPolicy:
    return TokenPolicy(
        access_token_expire_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )


def get_user_repository(
    db: DbSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> UserRepository:
    return SqlAlchemyUserRepository(db, clock)


def get_session_repository(db: DbSession = Depends(get_db)) -> SessionRepository:
    return SqlAlchemySessionRepository(db)


def get_refresh_token_repository(
    db: DbSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> RefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(db, clock)


def get_token_pair_issuer(
    refresh_token_repository: RefreshTokenRepository = Depends(get_refresh_token_repository),
    token_service: TokenService = Depends(get_token_service),
    refresh_token_service: RefreshTokenService = Depends(get_refresh_token_service),
    clock: Clock = Depends(get_clock),
    token_policy: TokenPolicy = Depends(get_token_policy),
    id_generator: IdGenerator = Depends(get_id_generator),
) -> TokenPairIssuer:
    return TokenPairIssuer(
        refresh_token_repository=refresh_token_repository,
        token_service=token_service,
        refresh_token_service=refresh_token_service,
        clock=clock,
        token_policy=token_policy,
        id_generator=id_generator,
    )


def get_login_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    session_repository: SessionRepository = Depends(get_session_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    token_pair_issuer: TokenPairIssuer = Depends(get_token_pair_issuer),
    clock: Clock = Depends(get_clock),
    id_generator: IdGenerator = Depends(get_id_generator),
) -> LoginUseCase:
    return LoginUseCase(
        user_repository=user_repository,
        session_repository=session_repository,
        password_hasher=password_hasher,
        token_pair_issuer=token_pair_issuer,
        clock=clock,
        id_generator=id_generator,
    )


def get_refresh_session_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    session_repository: SessionRepository = Depends(get_session_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(get_refresh_token_repository),
    refresh_token_service: RefreshTokenService = Depends(get_refresh_token_service),
    token_pair_issuer: TokenPairIssuer = Depends(get_token_pair_issuer),
    clock: Clock = Depends(get_clock),
) -> RefreshSessionUseCase:
    return RefreshSessionUseCase(
        user_repository=user_repository,
        session_repository=session_repository,
        refresh_token_repository=refresh_token_repository,
        refresh_token_service=refresh_token_service,
        token_pair_issuer=token_pair_issuer,
        clock=clock,
    )


def get_logout_use_case(
    session_repository: SessionRepository = Depends(get_session_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(get_refresh_token_repository),
    refresh_token_service: RefreshTokenService = Depends(get_refresh_token_service),
    clock: Clock = Depends(get_clock),
) -> LogoutUseCase:
    return LogoutUseCase(
        session_repository=session_repository,
        refresh_token_repository=refresh_token_repository,
        refresh_token_service=refresh_token_service,
        clock=clock,
    )
