import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import text


def _previous_migration_test():
    path = Path(__file__).with_name("test_migration_0070_fair_stand_item_prices_permissions.py")
    spec = importlib.util.spec_from_file_location("migration_0070_item_prices", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
PREVIOUS = "20261007_0070"
REVISION = "20261007_0071"
NEW_CODES = (
    "fair_crm.fair_stand.cost_items.create",
    "fair_crm.fair_stand.cost_items.delete",
    "fair_crm.fair_stand.cost_items.read",
    "fair_crm.fair_stand.cost_items.update",
)


def test_migration_0071_renames_permission_codes_and_keeps_role_grants(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    import app.core.config as core_config

    core_config.settings = core_config.Settings()
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url)

    previous = _previous_migration_test()
    previous._prepare_database_at_previous_revision(config)
    command.upgrade(config, PREVIOUS)

    engine = sa.create_engine(database_url)
    with engine.connect() as connection:
        before = connection.execute(
            text(
                """
                SELECT id, code
                FROM identity_permissions
                WHERE code LIKE 'fair_crm.fair_stand.item_prices.%'
                ORDER BY code
                """
            )
        ).all()
        grants_before = connection.execute(
            text(
                """
                SELECT r.slug, p.id
                FROM identity_role_permissions rp
                JOIN identity_roles r ON r.id = rp.role_id
                JOIN identity_permissions p ON p.id = rp.permission_id
                WHERE p.code LIKE 'fair_crm.fair_stand.item_prices.%'
                """
            )
        ).all()
    assert len(before) == 4
    ids_before = {row.id for row in before}

    command.upgrade(config, REVISION)
    assert previous._current_revision(config) == REVISION

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, code, is_system, lifecycle_state, is_assignable, permission_scope
                FROM identity_permissions
                WHERE code LIKE 'fair_crm.fair_stand.cost_items.%'
                ORDER BY code
                """
            )
        ).mappings().all()
        old_count = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM identity_permissions
                WHERE code LIKE 'fair_crm.fair_stand.item_prices.%'
                """
            )
        ).scalar_one()
        group_code = connection.execute(
            text("SELECT code FROM identity_permission_groups WHERE code = 'fair_crm.fair_stand.cost_items'")
        ).scalar_one()
        grants = connection.execute(
            text(
                """
                SELECT r.slug, p.id, p.code
                FROM identity_role_permissions rp
                JOIN identity_roles r ON r.id = rp.role_id
                JOIN identity_permissions p ON p.id = rp.permission_id
                WHERE p.code LIKE 'fair_crm.fair_stand.cost_items.%'
                """
            )
        ).all()

    assert old_count == 0
    assert group_code == "fair_crm.fair_stand.cost_items"
    assert [row["code"] for row in rows] == sorted(NEW_CODES)
    assert {row["id"] for row in rows} == ids_before
    for row in rows:
        assert bool(row["is_system"]) is True
        assert row["lifecycle_state"] == "active"
        assert bool(row["is_assignable"]) is True
        assert row["permission_scope"] == "organization"

    assert {(slug, permission_id) for slug, permission_id in grants_before} == {
        (slug, permission_id) for slug, permission_id, _code in grants
    }
    by_role: dict[str, set[str]] = {}
    for slug, _permission_id, code in grants:
        by_role.setdefault(slug, set()).add(code)
    assert by_role["organization_admin"] == set(NEW_CODES)
    assert by_role["full_user"] == set(NEW_CODES)
    assert by_role["read_user"] == {"fair_crm.fair_stand.cost_items.read"}
    assert by_role["create_update_user"] == {
        "fair_crm.fair_stand.cost_items.read",
        "fair_crm.fair_stand.cost_items.create",
        "fair_crm.fair_stand.cost_items.update",
    }
