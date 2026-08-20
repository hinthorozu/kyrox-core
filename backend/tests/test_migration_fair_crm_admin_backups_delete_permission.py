from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260821_0061"
PREVIOUS_REVISION = "20260820_0060"
PERMISSION_CODE = "fair_crm.admin.backups.delete"


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    database_url = f"sqlite:///{tmp_path / 'backup_delete_permission.db'}"
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
                    id TEXT NOT NULL PRIMARY KEY,
                    code VARCHAR(255) NOT NULL UNIQUE
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE identity_permissions (
                    id TEXT NOT NULL PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    code VARCHAR(255) NOT NULL UNIQUE,
                    description VARCHAR(512) NOT NULL,
                    is_system BOOLEAN NOT NULL,
                    lifecycle_state VARCHAR(32) NOT NULL,
                    is_assignable BOOLEAN NOT NULL,
                    permission_scope VARCHAR(32) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE identity_role_permissions (
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
                CREATE TABLE identity_role_template_exclusions (
                    role_id TEXT NOT NULL,
                    permission_id TEXT NOT NULL,
                    PRIMARY KEY (role_id, permission_id)
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO identity_permission_groups (id, code) "
                "VALUES ('backup-group', 'fair_crm.admin.backups')"
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_permissions (
                    id, group_id, code, description, is_system, lifecycle_state,
                    is_assignable, permission_scope
                ) VALUES (
                    'backup-read', 'backup-group', 'fair_crm.admin.backups.read',
                    'Read CRM database backups', 1, 'active', 0, 'system'
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


def test_backup_delete_permission_is_super_admin_only(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    assert _current_revision(alembic_config) == REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        permission = connection.execute(
            text(
                """
                SELECT group_id, lifecycle_state, is_assignable, permission_scope
                FROM identity_permissions WHERE code=:code
                """
            ),
            {"code": PERMISSION_CODE},
        ).one()
        grants = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM identity_role_permissions
                WHERE permission_id=(SELECT id FROM identity_permissions WHERE code=:code)
                """
            ),
            {"code": PERMISSION_CODE},
        ).scalar_one()

    assert permission[0] == "backup-group"
    assert permission[1] == "active"
    assert bool(permission[2]) is False
    assert permission[3] == "system"
    assert grants == 0


def test_backup_delete_permission_downgrade_removes_permission(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    assert _current_revision(alembic_config) == PREVIOUS_REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM identity_permissions WHERE code=:code"),
            {"code": PERMISSION_CODE},
        ).scalar_one()
    assert count == 0
