from datetime import UTC, datetime, timedelta
import uuid

import jwt
from app.core.config import settings
from app.modules.identity.domain.ports import AccessTokenClaims
from app.modules.identity.infrastructure.security.jwt_token_service import JwtTokenService


def test_jwt_token_service_creates_token_with_required_claims() -> None:
    service = JwtTokenService()
    now = datetime.now(UTC)
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    jti = uuid.uuid4()

    token = service.create_access_token(
        AccessTokenClaims(
            sub=user_id,
            email="user@example.com",
            sid=session_id,
            exp=now + timedelta(minutes=15),
            iat=now,
            jti=jti,
        )
    )

    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "user@example.com"
    assert payload["sid"] == str(session_id)
    assert payload["jti"] == str(jti)
    assert "exp" in payload
    assert "iat" in payload
    assert "org_id" not in payload


def test_jwt_token_service_decodes_token() -> None:
    service = JwtTokenService()
    now = datetime.now(UTC)
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    jti = uuid.uuid4()
    exp = now + timedelta(minutes=15)

    token = service.create_access_token(
        AccessTokenClaims(
            sub=user_id,
            email="user@example.com",
            sid=session_id,
            exp=exp,
            iat=now,
            jti=jti,
        )
    )

    claims = service.decode_access_token(token)
    assert claims.sub == user_id
    assert claims.email == "user@example.com"
    assert claims.sid == session_id
    assert claims.jti == jti
