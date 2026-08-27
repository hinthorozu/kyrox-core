from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent
_ENV_FILES = (
    str(_BACKEND_ROOT / ".env"),
    str(_REPO_ROOT / ".env"),
)


class Settings(BaseSettings):
    APP_NAME: str = "kyrox-core"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/kyrox_core"

    JWT_SECRET_KEY: str = "dev-insecure-change-me-use-env-in-production-32b"
    JWT_ALGORITHM: str = "HS256"
    # Access JWT lifetime in days (Fair CRM session alignment).
    ACCESS_TOKEN_EXPIRE_DAYS: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 15

    # Dedicated secret for reconstructable, hash-only persisted identity action
    # tokens used by asynchronous identity-email delivery.
    CORE_IDENTITY_ACTION_TOKEN_SECRET_KEY: str = (
        "dev-insecure-identity-action-token-secret-change-me"
    )
    CORE_IDENTITY_ACTION_TOKEN_TTL_HOURS: int = 24
    CORE_IDENTITY_ACTIVATION_URL_TEMPLATE: str = (
        "http://localhost:3000/activate?token={token}"
    )
    CORE_IDENTITY_PASSWORD_RESET_URL_TEMPLATE: str = (
        "http://localhost:3000/reset-password?token={token}"
    )

    # Core-owned identity/platform email. These credentials are deliberately
    # separate from product/tenant mail accounts such as FAIR CRM providers.
    CORE_EMAIL_PROVIDER: str = "log"
    CORE_EMAIL_FROM: str | None = None
    CORE_SMTP_HOST: str | None = None
    CORE_SMTP_PORT: int = 587
    CORE_SMTP_USERNAME: str | None = None
    CORE_SMTP_PASSWORD: str | None = None
    CORE_SMTP_STARTTLS: bool = True
    CORE_SMTP_SSL: bool = False
    CORE_SMTP_TIMEOUT_SECONDS: float = 10.0

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
