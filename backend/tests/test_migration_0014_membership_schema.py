import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260701_0016"
PREVIOUS_REVISION = "20260701_0013"
INTERMEDIATE_REVISION = "20260701_0015"
STAMP_REVISION = "20260701_0007"
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
    command.stamp(config, STAMP_REVISION)
    command.upgrade(config, PREVIOUS_REVISION)


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def _table_columns(engine: sa.Engine, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def test_migration_0014_to_0016_upgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    membership_columns = _table_columns(engine, "identity_memberships")

    assert "identity_membership_invites" in tables
    assert {"invited_at", "joined_at"}.issubset(membership_columns)
    assert "role_id" not in membership_columns

    invite_columns = _table_columns(engine, "identity_membership_invites")
    assert {
        "id",
        "organization_id",
        "email",
        "token_hash",
        "invited_by_user_id",
        "expires_at",
        "accepted_at",
        "revoked_at",
        "created_at",
    }.issubset(invite_columns)

    membership_indexes = {index["name"] for index in inspector.get_indexes("identity_memberships")}
    invite_indexes = {index["name"] for index in inspector.get_indexes("identity_membership_invites")}

    assert "ix_identity_memberships_org_effective" in membership_indexes
    assert "ix_identity_membership_invites_organization_id" in invite_indexes
    assert "ix_identity_membership_invites_pending_by_org" in invite_indexes


def test_migration_0014_to_0016_downgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    membership_columns = _table_columns(engine, "identity_memberships")

    assert "identity_membership_invites" not in tables
    assert "invited_at" not in membership_columns
    assert "joined_at" not in membership_columns
    assert "role_id" in membership_columns

    membership_indexes = {index["name"] for index in inspector.get_indexes("identity_memberships")}
    assert "ix_identity_memberships_org_effective" not in membership_indexes
    assert "ix_identity_memberships_role_id" in membership_indexes


def test_migration_0014_to_0016_smoke_roundtrip(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    assert _current_revision(alembic_config) == REVISION

    command.downgrade(alembic_config, PREVIOUS_REVISION)
    assert _current_revision(alembic_config) == PREVIOUS_REVISION

    command.upgrade(alembic_config, REVISION)
    assert _current_revision(alembic_config) == REVISION


def test_migration_0016_fails_when_role_id_orphans_exist(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, INTERMEDIATE_REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    user_id = str(uuid.uuid4())
    organization_id = str(uuid.uuid4())
    role_id = str(uuid.uuid4())
    membership_id = str(uuid.uuid4())

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO identity_users (
                    id, email, password_hash, status, is_super_admin,
                    created_at, updated_at, deleted_at
                ) VALUES (
                    :id, :email, NULL, 'active', 0,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL
                )
                """
            ),
            {"id": user_id, "email": "orphan-role@example.com"},
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_organizations (
                    id, name, slug, status, created_at, updated_at, deleted_at
                ) VALUES (
                    :id, 'Orphan Org', 'orphan-org', 'active',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL
                )
                """
            ),
            {"id": organization_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_roles (
                    id, name, slug, scope, is_system,
                    created_at, updated_at, deleted_at
                ) VALUES (
                    :id, 'Owner', 'owner', 'platform', 1,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL
                )
                """
            ),
            {"id": role_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_memberships (
                    id, user_id, organization_id, status, role_id,
                    created_at, updated_at, deleted_at
                ) VALUES (
                    :id, :user_id, :organization_id, 'active', :role_id,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL
                )
                """
            ),
            {
                "id": membership_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "role_id": role_id,
            },
        )

    with pytest.raises(RuntimeError, match="Cannot drop identity_memberships.role_id"):
        command.upgrade(alembic_config, REVISION)
