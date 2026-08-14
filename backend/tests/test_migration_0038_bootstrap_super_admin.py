from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
PREVIOUS_REVISION = "20260814_0037"
REVISION = "20260814_0038"


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    import app.core.config as core_config

    core_config.settings = core_config.Settings()

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _prepare_users_table(config: Config) -> sa.Engine:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE identity_users (
                    id TEXT NOT NULL PRIMARY KEY,
                    email VARCHAR(320) NOT NULL UNIQUE,
                    password_hash VARCHAR NULL,
                    status VARCHAR(32) NOT NULL,
                    is_super_admin BOOLEAN NOT NULL DEFAULT 0,
                    must_change_password BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted_at DATETIME NULL
                )
                """
            )
        )
    command.stamp(config, PREVIOUS_REVISION)
    return engine


def test_bootstrap_promotes_single_active_user(alembic_config: Config) -> None:
    engine = _prepare_users_table(alembic_config)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO identity_users (id, email, status, is_super_admin)
                VALUES ('00000000-0000-4000-8000-000000000001', 'dev@example.com', 'active', 0)
                """
            )
        )

    command.upgrade(alembic_config, REVISION)

    with engine.connect() as connection:
        is_super_admin = connection.execute(
            text("SELECT is_super_admin FROM identity_users WHERE email = 'dev@example.com'")
        ).scalar_one()

    assert bool(is_super_admin) is True


def test_bootstrap_does_not_guess_between_multiple_active_users(alembic_config: Config) -> None:
    engine = _prepare_users_table(alembic_config)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO identity_users (id, email, status, is_super_admin)
                VALUES
                    ('00000000-0000-4000-8000-000000000001', 'one@example.com', 'active', 0),
                    ('00000000-0000-4000-8000-000000000002', 'two@example.com', 'active', 0)
                """
            )
        )

    command.upgrade(alembic_config, REVISION)

    with engine.connect() as connection:
        super_admin_count = connection.execute(
            text("SELECT COUNT(*) FROM identity_users WHERE is_super_admin = 1")
        ).scalar_one()

    assert super_admin_count == 0
