from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260919_0066"
PREVIOUS_REVISION = "20260903_0065"
PERMISSION_CODES = (
    "fair_crm.admin.fair_stand.catalog.read",
    "fair_crm.admin.fair_stand.catalog.create",
    "fair_crm.admin.fair_stand.catalog.update",
    "fair_crm.admin.fair_stand.catalog.archive",
    "fair_crm.admin.fair_stand.previews.read",
    "fair_crm.admin.fair_stand.previews.create",
    "fair_crm.admin.fair_stand.previews.update",
    "fair_crm.admin.fair_stand.previews.archive",
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
                    code VARCHAR(255) NOT NULL UNIQUE
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
            text("INSERT INTO identity_permission_groups (id, code) VALUES ('group-1', 'identity')")
        )
    command.stamp(config, PREVIOUS_REVISION)


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def test_migration_0066_adds_non_assignable_system_fair_stand_admin_permissions(
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
                WHERE code LIKE 'fair_crm.admin.fair_stand.%'
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
                    WHERE code LIKE 'fair_crm.admin.fair_stand.%'
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


def test_migration_0066_repairs_preexisting_permission_and_removes_role_links(
    alembic_config: Config,
) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO identity_permissions (
                    id, group_id, code, description, is_system,
                    lifecycle_state, is_assignable, permission_scope,
                    created_at, updated_at
                ) VALUES (
                    'broken', 'group-1', 'fair_crm.admin.fair_stand.catalog.read',
                    'wrong', 0, 'retired', 1, 'organization',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text("INSERT INTO identity_role_permissions (role_id, permission_id) VALUES ('role-1', 'broken')")
        )

    command.upgrade(alembic_config, REVISION)
    with engine.connect() as connection:
        permission = connection.execute(
            text(
                """
                SELECT is_system, lifecycle_state, is_assignable, permission_scope
                FROM identity_permissions
                WHERE code='fair_crm.admin.fair_stand.catalog.read'
                """
            )
        ).mappings().one()
        assignments = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM identity_role_permissions
                WHERE permission_id=(
                    SELECT id FROM identity_permissions
                    WHERE code='fair_crm.admin.fair_stand.catalog.read'
                )
                """
            )
        ).scalar_one()

    assert bool(permission["is_system"]) is True
    assert permission["lifecycle_state"] == "active"
    assert bool(permission["is_assignable"]) is False
    assert permission["permission_scope"] == "system"
    assert assignments == 0
