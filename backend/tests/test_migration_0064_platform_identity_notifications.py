from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
REVISION = "20260827_0064"
PREVIOUS_REVISION = "20260827_0063"


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
                CREATE TABLE platform_jobs (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    organization_id CHAR(32) NOT NULL,
                    job_type VARCHAR(255) NOT NULL,
                    idempotency_key VARCHAR(128)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE platform_notifications (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    organization_id CHAR(32) NOT NULL,
                    idempotency_key VARCHAR(128)
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


def test_migration_0064_allows_platform_scope_and_enforces_idempotency(
    alembic_config: Config,
) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)

    assert _current_revision(alembic_config) == REVISION
    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    inspector = inspect(engine)
    job_columns = {column["name"]: column for column in inspector.get_columns("platform_jobs")}
    notification_columns = {
        column["name"]: column
        for column in inspector.get_columns("platform_notifications")
    }
    assert job_columns["organization_id"]["nullable"] is True
    assert notification_columns["organization_id"]["nullable"] is True

    job_indexes = {index["name"] for index in inspector.get_indexes("platform_jobs")}
    notification_indexes = {
        index["name"] for index in inspector.get_indexes("platform_notifications")
    }
    assert "uq_platform_jobs_platform_type_idempotency" in job_indexes
    assert "uq_platform_notifications_platform_idempotency" in notification_indexes

    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO platform_jobs (id, organization_id, job_type, idempotency_key) "
                "VALUES ('1', NULL, 'identity-mail', 'same-key')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO platform_notifications (id, organization_id, idempotency_key) "
                "VALUES ('1', NULL, 'same-key')"
            )
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO platform_jobs (id, organization_id, job_type, idempotency_key) "
                    "VALUES ('2', NULL, 'identity-mail', 'same-key')"
                )
            )
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO platform_notifications (id, organization_id, idempotency_key) "
                    "VALUES ('2', NULL, 'same-key')"
                )
            )


def test_migration_0064_downgrade_restores_organization_scope(
    alembic_config: Config,
) -> None:
    _prepare_database_at_previous_revision(alembic_config)
    command.upgrade(alembic_config, REVISION)
    command.downgrade(alembic_config, PREVIOUS_REVISION)

    engine = sa.create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    inspector = inspect(engine)
    job_columns = {column["name"]: column for column in inspector.get_columns("platform_jobs")}
    notification_columns = {
        column["name"]: column
        for column in inspector.get_columns("platform_notifications")
    }
    assert job_columns["organization_id"]["nullable"] is False
    assert notification_columns["organization_id"]["nullable"] is False
    assert _current_revision(alembic_config) == PREVIOUS_REVISION
