from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260701_0007"
PREVIOUS_REVISION = "20260701_0006"
BASE_AUTH_REVISION = "20260701_0003"


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    import app.core.config as core_config

    core_config.settings = core_config.Settings()

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _prepare_database_at_previous_revision(config: Config) -> None:
    command.upgrade(config, BASE_AUTH_REVISION)
    command.stamp(config, PREVIOUS_REVISION)


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def _session_columns(engine: sa.Engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("identity_sessions")}


def _refresh_token_columns(engine: sa.Engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("identity_refresh_tokens")}


def test_migration_0007_upgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    session_columns = _session_columns(engine)
    refresh_columns = _refresh_token_columns(engine)

    assert "last_activity_at" in session_columns
    assert "last_used_at" not in session_columns
    assert {"device_name", "client_fingerprint"}.issubset(session_columns)
    assert {
        "family_id",
        "rotated_from",
        "used_at",
        "revoked_reason",
        "reuse_detected_at",
        "created_by_ip",
        "created_by_user_agent",
    }.issubset(refresh_columns)

    indexes = {index["name"] for index in inspect(engine).get_indexes("identity_refresh_tokens")}
    assert "ix_identity_refresh_tokens_family_id" in indexes
    assert "ix_identity_refresh_tokens_active_by_session" in indexes


def test_migration_0007_downgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    session_columns = _session_columns(engine)
    refresh_columns = _refresh_token_columns(engine)

    assert "last_used_at" in session_columns
    assert "last_activity_at" not in session_columns
    assert "device_name" not in session_columns
    assert "client_fingerprint" not in session_columns
    assert "family_id" not in refresh_columns


def test_migration_0007_smoke_roundtrip(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    assert _current_revision(alembic_config) == REVISION

    command.downgrade(alembic_config, PREVIOUS_REVISION)
    assert _current_revision(alembic_config) == PREVIOUS_REVISION

    command.upgrade(alembic_config, REVISION)
    assert _current_revision(alembic_config) == REVISION
