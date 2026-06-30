from app.modules.identity.domain.ports import RefreshTokenService
from app.modules.identity.infrastructure.security.token_utils import (
    generate_refresh_token,
    hash_refresh_token,
)


class SecureRefreshTokenService:
    def generate(self) -> str:
        return generate_refresh_token()

    def hash_token(self, token: str) -> str:
        return hash_refresh_token(token)
