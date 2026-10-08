from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
PREVIOUS = "20261007_0071"
REVISION = "20261008_0072"
PREVIEW_CODES = (
    "fair_crm.admin.fair_stand.previews.archive",
    "fair_crm.admin.fair_stand.previews.create",
    "fair_crm.admin.fair_stand.previews.read",
    "fair_crm.admin.fair_stand.previews.update",
)
CATALOG_CODE = "fair_crm.admin.fair_stand.catalog.read"


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    import app.core.config as core_config

    core_config.settings = core_config.Settings()
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _prepare(config: Config) -> None:
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
            text(
                """
                INSERT INTO identity_permission_groups (id, code)
                VALUES ('group-fs', 'fair_crm.admin.fair_stand')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_permissions
                    (id, group_id, code, description, is_system, lifecycle_state,
                     is_assignable, permission_scope, created_at, updated_at)
                VALUES
                    ('perm-catalog', 'group-fs', :catalog_code, 'Read catalog', 1, 'active',
                     0, 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('perm-preview', 'group-fs', 'fair_crm.admin.fair_stand.previews.read',
                     'Read previews', 1, 'active', 0, 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('perm-preview-c', 'group-fs', 'fair_crm.admin.fair_stand.previews.create',
                     'Create previews', 1, 'active', 0, 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('perm-preview-u', 'group-fs', 'fair_crm.admin.fair_stand.previews.update',
                     'Update previews', 1, 'active', 0, 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('perm-preview-a', 'group-fs', 'fair_crm.admin.fair_stand.previews.archive',
                     'Archive previews', 1, 'active', 0, 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"catalog_code": CATALOG_CODE},
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_role_permissions (role_id, permission_id)
                VALUES ('role-1', 'perm-preview')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_role_template_exclusions (permission_id)
                VALUES ('perm-preview')
                """
            )
        )
    command.stamp(config, PREVIOUS)


def _revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def test_migration_0072_drops_preview_permissions_and_keeps_catalog(alembic_config: Config) -> None:
    _prepare(alembic_config)
    command.upgrade(alembic_config, REVISION)
    assert _revision(alembic_config) == REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        preview_count = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM identity_permissions
                WHERE code LIKE 'fair_crm.admin.fair_stand.previews.%'
                """
            )
        ).scalar_one()
        catalog = connection.execute(
            text("SELECT code FROM identity_permissions WHERE code=:code"),
            {"code": CATALOG_CODE},
        ).scalar_one()
        group = connection.execute(
            text("SELECT code FROM identity_permission_groups WHERE id='group-fs'")
        ).scalar_one()
        grants = connection.execute(text("SELECT COUNT(*) FROM identity_role_permissions")).scalar_one()
        exclusions = connection.execute(
            text("SELECT COUNT(*) FROM identity_role_template_exclusions")
        ).scalar_one()

    assert preview_count == 0
    assert catalog == CATALOG_CODE
    assert group == "fair_crm.admin.fair_stand"
    assert grants == 0
    assert exclusions == 0

    command.downgrade(alembic_config, PREVIOUS)
    assert _revision(alembic_config) == PREVIOUS
    with engine.connect() as connection:
        restored = connection.execute(
            text(
                """
                SELECT code FROM identity_permissions
                WHERE code LIKE 'fair_crm.admin.fair_stand.previews.%'
                ORDER BY code
                """
            )
        ).scalars().all()
    assert restored == sorted(PREVIEW_CODES)
