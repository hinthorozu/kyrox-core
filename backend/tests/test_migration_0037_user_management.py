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


def test_user_management_migration_matches_authorization_schema(alembic_config: Config) -> None:
    command.upgrade(alembic_config, PREVIOUS_REVISION)
    command.upgrade(alembic_config, REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
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
    command.upgrade(alembic_config, REVISION)
    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))

    with engine.begin() as connection:
        role_id = connection.execute(text("SELECT id FROM identity_roles LIMIT 1")).scalar()
        permission_id = connection.execute(
            text("SELECT id FROM identity_permissions WHERE code = 'identity.users.create'")
        ).scalar_one()
        if role_id is not None:
            connection.execute(
                text(
                    "INSERT INTO identity_role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :permission_id)"
                ),
                {"role_id": role_id, "permission_id": permission_id},
            )

    command.downgrade(alembic_config, PREVIOUS_REVISION)

    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("identity_users")}
    assert "must_change_password" not in user_columns

    with engine.connect() as connection:
        remaining = connection.execute(
            text(
                "SELECT COUNT(*) FROM identity_permissions "
                "WHERE code IN ('identity.users.read', 'identity.users.create', "
                "'identity.users.update', 'identity.roles.read', 'identity.roles.update')"
            )
        ).scalar_one()
    assert remaining == 0
