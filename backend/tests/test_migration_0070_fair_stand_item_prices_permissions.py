from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20261007_0070"
PREVIOUS_REVISION = "20260922_0069"
PERMISSION_CODES = (
    "fair_crm.fair_stand.item_prices.create",
    "fair_crm.fair_stand.item_prices.delete",
    "fair_crm.fair_stand.item_prices.read",
    "fair_crm.fair_stand.item_prices.update",
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
                CREATE TABLE identity_roles (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    organization_id VARCHAR(36),
                    slug VARCHAR(64) NOT NULL,
                    role_kind VARCHAR(32) NOT NULL,
                    deleted_at DATETIME,
                    template_version INTEGER NOT NULL DEFAULT 1,
                    source_template_role_id VARCHAR(36),
                    source_template_version INTEGER,
                    permissions_customized BOOLEAN NOT NULL DEFAULT 0,
                    updated_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE identity_role_permissions (
                    role_id VARCHAR(36) NOT NULL,
                    permission_id VARCHAR(36) NOT NULL,
                    UNIQUE (role_id, permission_id)
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
                INSERT INTO identity_roles
                    (id, organization_id, slug, role_kind, deleted_at, template_version,
                     permissions_customized, updated_at)
                VALUES
                    ('role-admin', NULL, 'organization_admin', 'template', NULL, 1, 0, CURRENT_TIMESTAMP),
                    ('role-full', NULL, 'full_user', 'template', NULL, 1, 0, CURRENT_TIMESTAMP),
                    ('role-read', NULL, 'read_user', 'template', NULL, 1, 0, CURRENT_TIMESTAMP),
                    ('role-edit', NULL, 'create_update_user', 'template', NULL, 1, 0, CURRENT_TIMESTAMP)
                """
            )
        )
    command.stamp(config, PREVIOUS_REVISION)


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def test_migration_0070_adds_assignable_organization_item_price_permissions(
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
                WHERE code LIKE 'fair_crm.fair_stand.item_prices.%'
                ORDER BY code
                """
            )
        ).mappings().all()
        grants = connection.execute(
            text(
                """
                SELECT r.slug, p.code
                FROM identity_role_permissions rp
                JOIN identity_roles r ON r.id = rp.role_id
                JOIN identity_permissions p ON p.id = rp.permission_id
                WHERE p.code LIKE 'fair_crm.fair_stand.item_prices.%'
                """
            )
        ).all()

    assert [row["code"] for row in rows] == sorted(PERMISSION_CODES)
    for row in rows:
        assert bool(row["is_system"]) is True
        assert row["lifecycle_state"] == "active"
        assert bool(row["is_assignable"]) is True
        assert row["permission_scope"] == "organization"

    by_role: dict[str, set[str]] = {}
    for slug, code in grants:
        by_role.setdefault(slug, set()).add(code)
    assert by_role["organization_admin"] == set(PERMISSION_CODES)
    assert by_role["full_user"] == set(PERMISSION_CODES)
    assert by_role["read_user"] == {"fair_crm.fair_stand.item_prices.read"}
    assert by_role["create_update_user"] == {
        "fair_crm.fair_stand.item_prices.read",
        "fair_crm.fair_stand.item_prices.create",
        "fair_crm.fair_stand.item_prices.update",
    }
