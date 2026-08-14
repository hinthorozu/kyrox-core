from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
PREVIOUS_REVISION = "20260809_0036"
REVISION = "20260814_0037"
PERMISSION_CODES = {
    "identity.users.read",
    "identity.users.create",
    "identity.users.update",
    "identity.roles.read",
    "identity.roles.update",
}


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    import app.core.config as core_config

    core_config.settings = core_config.Settings()

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _prepare_database_at_previous_revision(config: Config) -> sa.Engine:
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
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted_at DATETIME NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE identity_permission_groups (
                    id TEXT NOT NULL PRIMARY KEY,
                    code VARCHAR(255) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    module VARCHAR(64) NOT NULL,
                    description VARCHAR(512) NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_system BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                CREATE TABLE identity_roles (
                    id TEXT NOT NULL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) NOT NULL,
                    scope VARCHAR(32) NOT NULL,
                    is_system BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted_at DATETIME NULL
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
                INSERT INTO identity_permission_groups
                    (id, code, name, module, description, sort_order, is_system)
                VALUES
                    ('00000000-0000-0000-0000-000000000001', 'identity', 'Identity',
                     'identity', 'Identity permissions', 1, 1)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_roles
                    (id, name, slug, scope, is_system)
                VALUES
                    ('00000000-0000-0000-0000-000000000002', 'Member', 'member',
                     'organization', 1)
                """
            )
        )
    command.stamp(config, PREVIOUS_REVISION)
    return engine


def test_user_management_migration_matches_authorization_schema(alembic_config: Config) -> None:
    engine = _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("identity_users")}
    assert "must_change_password" in user_columns

    with engine.connect() as connection:
        identity_group_id = connection.execute(
            text("SELECT id FROM identity_permission_groups WHERE code = 'identity'")
        ).scalar_one()
        rows = connection.execute(
            text(
                "SELECT code, group_id FROM identity_permissions "
                "WHERE code IN ('identity.users.read', 'identity.users.create', "
                "'identity.users.update', 'identity.roles.read', 'identity.roles.update')"
            )
        ).all()

    assert {row.code for row in rows} == PERMISSION_CODES
    assert {str(row.group_id) for row in rows} == {str(identity_group_id)}


def test_user_management_migration_downgrade_cleans_role_links(alembic_config: Config) -> None:
    engine = _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    with engine.begin() as connection:
        permission_id = connection.execute(
            text("SELECT id FROM identity_permissions WHERE code = 'identity.users.create'")
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO identity_role_permissions (role_id, permission_id) "
                "VALUES (:role_id, :permission_id)"
            ),
            {
                "role_id": "00000000-0000-0000-0000-000000000002",
                "permission_id": permission_id,
            },
        )

    command.downgrade(alembic_config, PREVIOUS_REVISION)

    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("identity_users")}
    assert "must_change_password" not in user_columns

    with engine.connect() as connection:
        remaining_permissions = connection.execute(
            text(
                "SELECT COUNT(*) FROM identity_permissions "
                "WHERE code IN ('identity.users.read', 'identity.users.create', "
                "'identity.users.update', 'identity.roles.read', 'identity.roles.update')"
            )
        ).scalar_one()
        remaining_links = connection.execute(
            text("SELECT COUNT(*) FROM identity_role_permissions")
        ).scalar_one()

    assert remaining_permissions == 0
    assert remaining_links == 0
