from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260701_0030"
PREVIOUS_REVISION = "20260701_0029"
DASHBOARD_TODO_PERMISSION_CODES = (
    "fair_crm.dashboard.read",
    "fair_crm.todos.read",
    "fair_crm.todos.create",
    "fair_crm.todos.update",
    "fair_crm.todos.archive",
    "fair_crm.todos.delete",
    "fair_crm.todos.outcomes.read",
    "fair_crm.todos.outcomes.create",
    "fair_crm.todos.outcomes.update",
    "fair_crm.todos.outcomes.deactivate",
)
FAIR_EMAIL_PERMISSION_CODES = (
    "fair_crm.fair_emails.preview",
    "fair_crm.fair_emails.send",
)


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    database_url = f"sqlite:///{tmp_path / 'fair_crm_dashboard_todos_permissions.db'}"
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


def _seed_fair_emails_group(engine: sa.Engine) -> None:
    import uuid

    group_id = str(uuid.uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO identity_permission_groups (
                    id, code, name, module, description, sort_order, is_system, created_at, updated_at
                ) VALUES (
                    :id, :code, :name, :module, :description, :sort_order, :is_system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": group_id,
                "code": "fair_crm.fair_emails",
                "name": "FAIR CRM Fair Emails",
                "module": "fair_crm",
                "description": "FAIR CRM fair bulk email permissions",
                "sort_order": 86,
                "is_system": True,
            },
        )
        for code in FAIR_EMAIL_PERMISSION_CODES:
            connection.execute(
                text(
                    """
                    INSERT INTO identity_permissions (
                        id, group_id, code, description, is_system, created_at, updated_at
                    ) VALUES (
                        :id, :group_id, :code, :description, :is_system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "group_id": group_id,
                    "code": code,
                    "description": code,
                    "is_system": True,
                },
            )


def _prepare_database_at_previous_revision(config: Config) -> None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    _bootstrap_permission_tables(engine)
    _seed_fair_emails_group(engine)
    command.stamp(config, PREVIOUS_REVISION)


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


def _permission_count(engine: sa.Engine, codes: tuple[str, ...]) -> int:
    placeholders = ", ".join(f"'{code}'" for code in codes)
    with engine.connect() as connection:
        return int(
            connection.execute(
                text(f"SELECT COUNT(*) FROM identity_permissions WHERE code IN ({placeholders})")
            ).scalar()
            or 0
        )


def test_fair_crm_dashboard_todos_permissions_upgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    assert _current_revision(alembic_config) == REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    assert _permission_codes(engine, DASHBOARD_TODO_PERMISSION_CODES) == set(
        DASHBOARD_TODO_PERMISSION_CODES
    )
    assert _permission_codes(engine, FAIR_EMAIL_PERMISSION_CODES) == set(FAIR_EMAIL_PERMISSION_CODES)

    with engine.connect() as connection:
        dashboard_group = connection.execute(
            text(
                """
                SELECT code, name, module FROM identity_permission_groups
                WHERE code = 'fair_crm.dashboard'
                LIMIT 1
                """
            )
        ).one()
        todos_group = connection.execute(
            text(
                """
                SELECT code, name, module FROM identity_permission_groups
                WHERE code = 'fair_crm.todos'
                LIMIT 1
                """
            )
        ).one()
        outcomes_group = connection.execute(
            text(
                """
                SELECT code, name, module FROM identity_permission_groups
                WHERE code = 'fair_crm.todos.outcomes'
                LIMIT 1
                """
            )
        ).one()

    assert dashboard_group[0] == "fair_crm.dashboard"
    assert todos_group[0] == "fair_crm.todos"
    assert outcomes_group[0] == "fair_crm.todos.outcomes"


def test_fair_crm_dashboard_todos_permissions_upgrade_is_idempotent(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    first_count = _permission_count(engine, DASHBOARD_TODO_PERMISSION_CODES)

    command.upgrade(alembic_config, REVISION)
    second_count = _permission_count(engine, DASHBOARD_TODO_PERMISSION_CODES)

    assert first_count == len(DASHBOARD_TODO_PERMISSION_CODES)
    assert second_count == first_count


def test_fair_crm_dashboard_todos_permissions_downgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    assert _current_revision(alembic_config) == PREVIOUS_REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    assert _permission_codes(engine, DASHBOARD_TODO_PERMISSION_CODES) == set()
    assert _permission_codes(engine, FAIR_EMAIL_PERMISSION_CODES) == set(FAIR_EMAIL_PERMISSION_CODES)

    with engine.connect() as connection:
        group_count = int(
            connection.execute(
                text(
                    """
                    SELECT COUNT(*) FROM identity_permission_groups
                    WHERE code IN ('fair_crm.dashboard', 'fair_crm.todos', 'fair_crm.todos.outcomes')
                    """
                )
            ).scalar()
            or 0
        )
    assert group_count == 0
