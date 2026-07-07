from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260701_0028"
PREVIOUS_REVISION = "20260701_0027"
TEST_SEND_PERMISSION = "fair_crm.mail_templates.test_send"
MAIL_TEMPLATE_PERMISSION_CODES = (
    "fair_crm.mail_templates.read",
    "fair_crm.mail_templates.create",
    "fair_crm.mail_templates.update",
    "fair_crm.mail_templates.delete",
    "fair_crm.mail_templates.render",
    TEST_SEND_PERMISSION,
)


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    database_url = f"sqlite:///{tmp_path / 'fair_crm_mail_templates_test_send.db'}"
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


def _seed_mail_templates_group(engine: sa.Engine) -> None:
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
                "code": "fair_crm.mail_templates",
                "name": "FAIR CRM Mail Templates",
                "module": "fair_crm",
                "description": "FAIR CRM mail template permissions",
                "sort_order": 85,
                "is_system": True,
            },
        )
        for code in MAIL_TEMPLATE_PERMISSION_CODES[:-1]:
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
    _seed_mail_templates_group(engine)
    command.stamp(config, PREVIOUS_REVISION)


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def test_fair_crm_mail_templates_test_send_permission_upgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    assert _current_revision(alembic_config) == REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT code FROM identity_permissions WHERE code = :code"),
            {"code": TEST_SEND_PERMISSION},
        ).one()
    assert row[0] == TEST_SEND_PERMISSION


def test_fair_crm_mail_templates_test_send_permission_downgrade(alembic_config: Config) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    assert _current_revision(alembic_config) == PREVIOUS_REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM identity_permissions WHERE code = :code"),
            {"code": TEST_SEND_PERMISSION},
        ).scalar()
    assert int(count or 0) == 0
