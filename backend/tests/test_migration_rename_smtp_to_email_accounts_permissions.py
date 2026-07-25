from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260701_0032"
PREVIOUS_REVISION = "20260701_0031"
OLD_PERMISSION_CODES = (
    "fair_crm.smtp.read",
    "fair_crm.smtp.create",
    "fair_crm.smtp.update",
    "fair_crm.smtp.delete",
)
NEW_PERMISSION_CODES = (
    "fair_crm.email_accounts.read",
    "fair_crm.email_accounts.create",
    "fair_crm.email_accounts.update",
    "fair_crm.email_accounts.delete",
)


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    database_url = f"sqlite:///{tmp_path / 'rename_smtp_email_accounts_permissions.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    import app.core.config as core_config

    core_config.settings = core_config.Settings()

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _bootstrap_permission_tables(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS identity_permission_groups (
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
                CREATE TABLE IF NOT EXISTS identity_permissions (
                    id TEXT NOT NULL PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    code VARCHAR(255) NOT NULL UNIQUE,
                    description VARCHAR(512) NOT NULL,
                    is_system BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(group_id) REFERENCES identity_permission_groups(id)
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


def _seed_smtp_group_with_grant(engine: sa.Engine) -> dict[str, str]:
    """Seed pre-rename smtp permissions and one role grant; return old_code → permission_id."""
    import uuid

    group_id = str(uuid.uuid4())
    role_id = str(uuid.uuid4())
    ids: dict[str, str] = {}
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO identity_permission_groups (
                    id, code, name, module, description, sort_order, is_system, created_at, updated_at
                ) VALUES (
                    :id, :code, :name, :module, :description, :sort_order, :is_system,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": group_id,
                "code": "fair_crm.smtp",
                "name": "FAIR CRM SMTP",
                "module": "fair_crm",
                "description": "FAIR CRM SMTP account permissions",
                "sort_order": 80,
                "is_system": True,
            },
        )
        for code in OLD_PERMISSION_CODES:
            permission_id = str(uuid.uuid4())
            ids[code] = permission_id
            connection.execute(
                text(
                    """
                    INSERT INTO identity_permissions (
                        id, group_id, code, description, is_system, created_at, updated_at
                    ) VALUES (
                        :id, :group_id, :code, :description, :is_system,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": permission_id,
                    "group_id": group_id,
                    "code": code,
                    "description": code,
                    "is_system": True,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO identity_role_permissions (role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                    """
                ),
                {"role_id": role_id, "permission_id": permission_id},
            )
    return ids


def _prepare_database_at_previous_revision(config: Config) -> dict[str, str]:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    _bootstrap_permission_tables(engine)
    ids = _seed_smtp_group_with_grant(engine)
    command.stamp(config, PREVIOUS_REVISION)
    return ids


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def _permission_codes(engine: sa.Engine, codes: tuple[str, ...]) -> set[str]:
    placeholders = ", ".join(f"'{code}'" for code in codes)
    with engine.connect() as connection:
        rows = connection.execute(
            text(f"SELECT code FROM identity_permissions WHERE code IN ({placeholders})")
        ).fetchall()
    return {row[0] for row in rows}


def _permission_id_by_code(engine: sa.Engine, code: str) -> str | None:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT id FROM identity_permissions WHERE code = :code LIMIT 1"),
            {"code": code},
        ).fetchone()
    return str(row[0]) if row else None


def test_rename_smtp_to_email_accounts_permissions_upgrade(alembic_config: Config) -> None:
    old_ids = _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    assert _current_revision(alembic_config) == REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    assert _permission_codes(engine, NEW_PERMISSION_CODES) == set(NEW_PERMISSION_CODES)
    assert _permission_codes(engine, OLD_PERMISSION_CODES) == set()

    with engine.connect() as connection:
        group = connection.execute(
            text(
                """
                SELECT code, name FROM identity_permission_groups
                WHERE code = 'fair_crm.email_accounts'
                LIMIT 1
                """
            )
        ).one()
        grant_count = connection.execute(
            text("SELECT COUNT(*) FROM identity_role_permissions")
        ).scalar()

    assert group[0] == "fair_crm.email_accounts"
    assert "Email Accounts" in group[1]
    assert int(grant_count or 0) == len(OLD_PERMISSION_CODES)

    # Same permission IDs → existing role grants stay valid.
    assert _permission_id_by_code(engine, "fair_crm.email_accounts.read") == old_ids[
        "fair_crm.smtp.read"
    ]
    assert _permission_id_by_code(engine, "fair_crm.email_accounts.create") == old_ids[
        "fair_crm.smtp.create"
    ]


def test_rename_smtp_to_email_accounts_permissions_idempotent_upgrade(
    alembic_config: Config,
) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.upgrade(alembic_config, REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    assert _permission_codes(engine, NEW_PERMISSION_CODES) == set(NEW_PERMISSION_CODES)
    assert _permission_codes(engine, OLD_PERMISSION_CODES) == set()


def test_rename_smtp_to_email_accounts_permissions_downgrade(alembic_config: Config) -> None:
    old_ids = _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    assert _current_revision(alembic_config) == PREVIOUS_REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    assert _permission_codes(engine, OLD_PERMISSION_CODES) == set(OLD_PERMISSION_CODES)
    assert _permission_codes(engine, NEW_PERMISSION_CODES) == set()
    assert _permission_id_by_code(engine, "fair_crm.smtp.read") == old_ids["fair_crm.smtp.read"]
