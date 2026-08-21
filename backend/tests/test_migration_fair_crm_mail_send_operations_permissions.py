from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260821_0062"
PREVIOUS_REVISION = "20260821_0061"
READ_CODE = "fair_crm.mail_send_operations.read"
EXECUTE_CODE = "fair_crm.mail_send_operations.execute"


@pytest.fixture
def alembic_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    database_url = f"sqlite:///{tmp_path / 'mail_send_permissions.db'}"
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
                    code VARCHAR(255) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    module VARCHAR(255) NOT NULL,
                    description VARCHAR(512),
                    sort_order INTEGER NOT NULL DEFAULT 0,
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
                """
                INSERT INTO identity_permission_groups
                    (id, code, name, module, description, sort_order, is_system)
                VALUES
                    ('email-group', 'fair_crm.email_accounts', 'Email Accounts', 'fair_crm',
                     'Email account permissions', 60, 1)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_permissions
                    (id, group_id, code, description, is_system, lifecycle_state,
                     is_assignable, permission_scope)
                VALUES
                    ('email-read', 'email-group', 'fair_crm.email_accounts.read',
                     'Read CRM email accounts', 1, 'active', 1, 'organization'),
                    ('email-update', 'email-group', 'fair_crm.email_accounts.update',
                     'Update CRM email accounts', 1, 'active', 1, 'organization')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_role_permissions (role_id, permission_id)
                VALUES
                    ('reader-role', 'email-read'),
                    ('sender-role', 'email-update'),
                    ('full-role', 'email-read'),
                    ('full-role', 'email-update')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_role_template_exclusions (role_id, permission_id)
                VALUES ('excluded-role', 'email-update')
                """
            )
        )
    command.stamp(config, PREVIOUS_REVISION)


def _current_revision(config: Config) -> str | None:
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def test_mail_send_permissions_are_org_scoped_and_preserve_existing_access(
    alembic_config: Config,
) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    assert _current_revision(alembic_config) == REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        group = connection.execute(
            text(
                """
                SELECT name, module, description, sort_order, is_system
                FROM identity_permission_groups
                WHERE code='fair_crm.mail_send_operations'
                """
            )
        ).one()
        rows = connection.execute(
            text(
                """
                SELECT p.code, g.code, p.lifecycle_state, p.is_assignable, p.permission_scope
                FROM identity_permissions AS p
                JOIN identity_permission_groups AS g ON g.id=p.group_id
                WHERE p.code IN (:read_code, :execute_code)
                ORDER BY p.code
                """
            ),
            {"read_code": READ_CODE, "execute_code": EXECUTE_CODE},
        ).all()
        grants = connection.execute(
            text(
                """
                SELECT rp.role_id, p.code
                FROM identity_role_permissions AS rp
                JOIN identity_permissions AS p ON p.id=rp.permission_id
                WHERE p.code IN (:read_code, :execute_code)
                ORDER BY rp.role_id, p.code
                """
            ),
            {"read_code": READ_CODE, "execute_code": EXECUTE_CODE},
        ).all()
        exclusions = connection.execute(
            text(
                """
                SELECT e.role_id, p.code
                FROM identity_role_template_exclusions AS e
                JOIN identity_permissions AS p ON p.id=e.permission_id
                WHERE p.code=:execute_code
                """
            ),
            {"execute_code": EXECUTE_CODE},
        ).all()
        email_execute_count = connection.execute(
            text("SELECT COUNT(*) FROM identity_permissions WHERE code='fair_crm.email_accounts.execute'")
        ).scalar_one()

    assert group == (
        "FAIR CRM Mail Send Operations",
        "fair_crm",
        "FAIR CRM mail send operation permissions",
        70,
        1,
    )
    assert rows == [
        (EXECUTE_CODE, "fair_crm.mail_send_operations", "active", 1, "organization"),
        (READ_CODE, "fair_crm.mail_send_operations", "active", 1, "organization"),
    ]
    assert grants == [
        ("full-role", EXECUTE_CODE),
        ("full-role", READ_CODE),
        ("reader-role", READ_CODE),
        ("sender-role", EXECUTE_CODE),
    ]
    assert exclusions == [("excluded-role", EXECUTE_CODE)]
    assert email_execute_count == 0


def test_mail_send_permissions_downgrade_removes_new_catalog_entries(
    alembic_config: Config,
) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    assert _current_revision(alembic_config) == PREVIOUS_REVISION

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        permissions = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM identity_permissions
                WHERE code IN (:read_code, :execute_code)
                """
            ),
            {"read_code": READ_CODE, "execute_code": EXECUTE_CODE},
        ).scalar_one()
        groups = connection.execute(
            text("SELECT COUNT(*) FROM identity_permission_groups WHERE code=:code"),
            {"code": "fair_crm.mail_send_operations"},
        ).scalar_one()

    assert permissions == 0
    assert groups == 0
