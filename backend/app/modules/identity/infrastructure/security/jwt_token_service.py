from datetime import UTC, datetime
from uuid import UUID

import jwt

from app.core.config import settings
from app.modules.identity.domain.ports import AccessTokenClaims, TokenService


class JwtTokenService:
    def create_access_token(self, claims: AccessTokenClaims) -> str:
        payload = {
            "sub": str(claims.sub),
            "email": claims.email,
            "sid": str(claims.sid),
            "exp": claims.exp,
            "iat": claims.iat,
            "jti": str(claims.jti),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return AccessTokenClaims(
            sub=UUID(payload["sub"]),
            email=payload["email"],
            sid=UUID(payload["sid"]),
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            jti=UUID(payload["jti"]),
        )
