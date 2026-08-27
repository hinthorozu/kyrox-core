from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260827_0063"
PREVIOUS_REVISION = "20260821_0062"


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
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE identity_users (
                    id CHAR(32) NOT NULL PRIMARY KEY
                )
                """
            )
        )
    command.stamp(config, PREVIOUS_REVISION)


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def test_migration_0063_creates_hash_only_action_token_schema(
    alembic_config: Config,
) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    assert _current_revision(alembic_config) == REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("identity_action_tokens")}

    assert columns == {
        "id",
        "user_id",
        "purpose",
        "token_hash",
        "expires_at",
        "consumed_at",
        "invalidated_at",
        "created_at",
    }
    assert "raw_token" not in columns
    assert "token" not in columns

    indexes = {index["name"] for index in inspector.get_indexes("identity_action_tokens")}
    assert "ix_identity_action_tokens_user_purpose" in indexes

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("identity_action_tokens")
    }
    assert "uq_identity_action_tokens_token_hash" in unique_constraints


def test_migration_0063_downgrade_removes_action_token_table(
    alembic_config: Config,
) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    assert "identity_action_tokens" not in inspect(engine).get_table_names()
    assert _current_revision(alembic_config) == PREVIOUS_REVISION
