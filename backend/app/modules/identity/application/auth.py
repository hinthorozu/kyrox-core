from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import settings
from app.db.utils import generate_uuid, utc_now
from app.modules.identity.application.dto import AuthTokenPair
from app.modules.identity.domain.entities import RefreshToken, Session
from app.modules.identity.domain.enums import UserStatus
from app.modules.identity.domain.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.modules.identity.domain.ports import (
    AccessTokenClaims,
    PasswordHasher,
    RefreshTokenRepository,
    RefreshTokenService,
    SessionRepository,
    TokenService,
    UserRepository,
)


class LoginUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        refresh_token_service: RefreshTokenService,
    ) -> None:
        self._user_repository = user_repository
        self._session_repository = session_repository
        self._refresh_token_repository = refresh_token_repository
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._refresh_token_service = refresh_token_service

    def execute(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthTokenPair:
        normalized_email = email.strip().lower()
        user = self._user_repository.get_by_email(normalized_email)
        if user is None or user.password_hash is None:
            raise InvalidCredentialsError("Invalid email or password")

        if user.deleted_at is not None or user.status is not UserStatus.ACTIVE:
            raise InactiveUserError("User account is not active")

        if not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        now = utc_now()
        session = self._session_repository.create(
            Session(
                id=generate_uuid(),
                user_id=user.id,
                created_at=now,
                updated_at=now,
                last_used_at=now,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )

        return self._issue_token_pair(user.id, user.email, session.id)

    def _issue_token_pair(self, user_id: UUID, email: str, session_id: UUID) -> AuthTokenPair:
        now = utc_now()
        access_expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        jti = generate_uuid()
        access_token = self._token_service.create_access_token(
            AccessTokenClaims(
                sub=user_id,
                email=email,
                sid=session_id,
                exp=access_expires_at,
                iat=now,
                jti=jti,
            )
        )

        raw_refresh_token = self._refresh_token_service.generate()
        self._refresh_token_repository.create(
            RefreshToken(
                id=generate_uuid(),
                session_id=session_id,
                token_hash=self._refresh_token_service.hash_token(raw_refresh_token),
                expires_at=refresh_expires_at,
                created_at=now,
            )
        )

        return AuthTokenPair(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


class RefreshSessionUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        token_service: TokenService,
        refresh_token_service: RefreshTokenService,
    ) -> None:
        self._user_repository = user_repository
        self._session_repository = session_repository
        self._refresh_token_repository = refresh_token_repository
        self._token_service = token_service
        self._refresh_token_service = refresh_token_service

    def execute(self, refresh_token: str) -> AuthTokenPair:
        token_hash = self._refresh_token_service.hash_token(refresh_token)
        stored_token = self._refresh_token_repository.get_by_token_hash(token_hash)
        if stored_token is None:
            raise InvalidRefreshTokenError("Invalid refresh token")

        now = utc_now()
        if stored_token.revoked_at is not None:
            raise InvalidRefreshTokenError("Refresh token has been revoked")

        expires_at = stored_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            raise InvalidRefreshTokenError("Refresh token has expired")

        session = self._session_repository.get_by_id(stored_token.session_id)
        if session is None or session.revoked_at is not None:
            raise InvalidRefreshTokenError("Session is no longer active")

        user = self._user_repository.get_by_id(session.user_id)
        if user is None or user.deleted_at is not None or user.status is not UserStatus.ACTIVE:
            raise InvalidRefreshTokenError("User account is not active")

        session.last_used_at = now
        session.updated_at = now
        self._session_repository.update(session)

        self._refresh_token_repository.revoke(stored_token.id, now)

        refresh_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        raw_refresh_token = self._refresh_token_service.generate()
        self._refresh_token_repository.create(
            RefreshToken(
                id=generate_uuid(),
                session_id=session.id,
                token_hash=self._refresh_token_service.hash_token(raw_refresh_token),
                expires_at=refresh_expires_at,
                created_at=now,
            )
        )

        jti = generate_uuid()
        access_expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self._token_service.create_access_token(
            AccessTokenClaims(
                sub=user.id,
                email=user.email,
                sid=session.id,
                exp=access_expires_at,
                iat=now,
                jti=jti,
            )
        )

        return AuthTokenPair(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


class LogoutUseCase:
    def __init__(
        self,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        refresh_token_service: RefreshTokenService,
    ) -> None:
        self._session_repository = session_repository
        self._refresh_token_repository = refresh_token_repository
        self._refresh_token_service = refresh_token_service

    def execute(self, refresh_token: str) -> None:
        token_hash = self._refresh_token_service.hash_token(refresh_token)
        stored_token = self._refresh_token_repository.get_by_token_hash(token_hash)
        if stored_token is None:
            return

        now = utc_now()
        if stored_token.revoked_at is None:
            self._refresh_token_repository.revoke(stored_token.id, now)

        self._session_repository.revoke(stored_token.session_id, now)
