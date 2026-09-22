from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260922_0068"
PREVIOUS_REVISION = "20260922_0067"
PERMISSION_CODES = (
    "fair_crm.admin.fair_stand.settings.read",
    "fair_crm.admin.fair_stand.settings.update",
)


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
                CREATE TABLE identity_permission_groups (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    code VARCHAR(255) NOT NULL UNIQUE,
                    name VARCHAR(255),
                    module VARCHAR(64),
                    description VARCHAR(512),
                    sort_order INTEGER,
                    is_system BOOLEAN,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE identity_permissions (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    group_id VARCHAR(36) NOT NULL,
                    code VARCHAR(255) NOT NULL UNIQUE,
                    description VARCHAR(512) NOT NULL,
                    is_system BOOLEAN NOT NULL,
                    lifecycle_state VARCHAR(32) NOT NULL,
                    is_assignable BOOLEAN NOT NULL,
                    permission_scope VARCHAR(32) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE identity_role_permissions (
                    role_id VARCHAR(36) NOT NULL,
                    permission_id VARCHAR(36) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE identity_role_template_exclusions (
                    permission_id VARCHAR(36) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_permission_groups
                    (id, code, name, module, description, sort_order, is_system, created_at, updated_at)
                VALUES
                    ('group-fs', 'fair_crm.admin.fair_stand', 'FAIR CRM Fair Stand Admin', 'fair_crm',
                     'existing', 96, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
    command.stamp(config, PREVIOUS_REVISION)


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def test_migration_0068_adds_non_assignable_system_fair_stand_settings_permissions(
    alembic_config: Config,
) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    assert _current_revision(alembic_config) == REVISION
    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT code, is_system, lifecycle_state, is_assignable, permission_scope
                FROM identity_permissions
                WHERE code LIKE 'fair_crm.admin.fair_stand.settings.%'
                ORDER BY code
                """
            )
        ).mappings().all()
        assignments = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM identity_role_permissions
                WHERE permission_id IN (
                    SELECT id FROM identity_permissions
                    WHERE code LIKE 'fair_crm.admin.fair_stand.settings.%'
                )
                """
            )
        ).scalar_one()

    assert [row["code"] for row in rows] == sorted(PERMISSION_CODES)
    for row in rows:
        assert bool(row["is_system"]) is True
        assert row["lifecycle_state"] == "active"
        assert bool(row["is_assignable"]) is False
        assert row["permission_scope"] == "system"
    assert assignments == 0
