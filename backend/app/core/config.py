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

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
