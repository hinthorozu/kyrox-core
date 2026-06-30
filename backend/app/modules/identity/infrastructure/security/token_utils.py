import hashlib
import secrets


def generate_refresh_token() -> str:
    """Return a cryptographically secure opaque refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage. Never persist the raw token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
