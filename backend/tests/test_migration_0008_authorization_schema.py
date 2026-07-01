from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260701_0013"
PREVIOUS_REVISION = "20260701_0007"
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


def _bootstrap_legacy_authorization_schema(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS identity_permissions (
                    id TEXT NOT NULL PRIMARY KEY,
                    code VARCHAR(255) NOT NULL UNIQUE,
                    description VARCHAR(512) NOT NULL,
                    module VARCHAR(64) NOT NULL,
                    is_system BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS identity_roles (
                    id TEXT NOT NULL PRIMARY KEY,
                    organization_id TEXT NULL,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) NOT NULL,
                    is_system BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted_at DATETIME NULL,
                    CONSTRAINT uq_identity_roles_organization_slug UNIQUE (organization_id, slug)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS identity_role_permissions (
                    role_id TEXT NOT NULL,
                    permission_id TEXT NOT NULL,
                    PRIMARY KEY (role_id, permission_id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_identity_roles_organization_id
                ON identity_roles (organization_id)
                """
            )
        )
        columns = {column["name"] for column in inspect(connection).get_columns("identity_memberships")}
        if "role_id" not in columns:
            connection.execute(text("ALTER TABLE identity_memberships ADD COLUMN role_id TEXT NULL"))


def _prepare_database_at_previous_revision(config: Config) -> None:
    command.upgrade(config, BASE_AUTH_REVISION)
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    _bootstrap_legacy_authorization_schema(engine)
    command.stamp(config, PREVIOUS_REVISION)


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def _table_columns(engine: sa.Engine, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def test_migration_0008_to_0013_upgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert "identity_permission_groups" in tables
    assert "identity_organization_roles" in tables
    assert "identity_user_roles" in tables

    role_columns = _table_columns(engine, "identity_roles")
    permission_columns = _table_columns(engine, "identity_permissions")

    assert "scope" in role_columns
    assert "organization_id" not in role_columns
    assert "group_id" in permission_columns
    assert "module" not in permission_columns

    indexes = {index["name"] for index in inspector.get_indexes("identity_user_roles")}
    assert "ix_identity_user_roles_user_org" in indexes
    assert "ix_identity_user_roles_effective" in indexes


def test_migration_0008_to_0013_downgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert "identity_permission_groups" not in tables
    assert "identity_organization_roles" not in tables
    assert "identity_user_roles" not in tables

    role_columns = _table_columns(engine, "identity_roles")
    permission_columns = _table_columns(engine, "identity_permissions")

    assert "organization_id" in role_columns
    assert "scope" not in role_columns
    assert "module" in permission_columns
    assert "group_id" not in permission_columns


def test_migration_0008_to_0013_smoke_roundtrip(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    assert _current_revision(alembic_config) == REVISION

    command.downgrade(alembic_config, PREVIOUS_REVISION)
    assert _current_revision(alembic_config) == PREVIOUS_REVISION

    command.upgrade(alembic_config, REVISION)
    assert _current_revision(alembic_config) == REVISION
