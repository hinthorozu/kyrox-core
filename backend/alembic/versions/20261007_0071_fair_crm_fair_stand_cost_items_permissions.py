"""Rename fair_crm.fair_stand.item_prices.* to fair_crm.fair_stand.cost_items.*.

Keeps the same permission row IDs so existing identity_role_permissions grants
remain valid. Scope stays organization and assignable.

Revision ID: 20261007_0071
Revises: 20261007_0070
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261007_0071"
down_revision = "20261007_0070"
branch_labels = None
depends_on = None

GROUPS_TABLE = "identity_permission_groups"
PERMISSIONS_TABLE = "identity_permissions"

PERMISSION_RENAMES: tuple[tuple[str, str, str], ...] = (
    (
        "fair_crm.fair_stand.item_prices.read",
        "fair_crm.fair_stand.cost_items.read",
        "Read Fair Stand cost items",
    ),
    (
        "fair_crm.fair_stand.item_prices.create",
        "fair_crm.fair_stand.cost_items.create",
        "Create Fair Stand cost items",
    ),
    (
        "fair_crm.fair_stand.item_prices.update",
        "fair_crm.fair_stand.cost_items.update",
        "Update Fair Stand cost items",
    ),
    (
        "fair_crm.fair_stand.item_prices.delete",
        "fair_crm.fair_stand.cost_items.delete",
        "Delete Fair Stand cost items",
    ),
)

GROUP_OLD = "fair_crm.fair_stand.item_prices"
GROUP_NEW = "fair_crm.fair_stand.cost_items"
GROUP_NEW_NAME = "FAIR CRM Fair Stand Cost Items"
GROUP_NEW_DESCRIPTION = "Organization-scoped Fair Stand cost item purchase and sale price permissions"
GROUP_OLD_NAME = "FAIR CRM Fair Stand Item Prices"
GROUP_OLD_DESCRIPTION = "Organization-scoped Fair Stand item purchase and sale price permissions"


def _rename_permission(connection: sa.Connection, old_code: str, new_code: str, description: str) -> None:
    connection.execute(
        sa.text(
            f"""
            UPDATE {PERMISSIONS_TABLE}
            SET code = :new_code,
                description = :description,
                updated_at = CURRENT_TIMESTAMP
            WHERE code = :old_code
            """
        ),
        {"old_code": old_code, "new_code": new_code, "description": description},
    )


def _rename_group(
    connection: sa.Connection,
    *,
    old_code: str,
    new_code: str,
    name: str,
    description: str,
) -> None:
    connection.execute(
        sa.text(
            f"""
            UPDATE {GROUPS_TABLE}
            SET code = :new_code,
                name = :name,
                description = :description,
                updated_at = CURRENT_TIMESTAMP
            WHERE code = :old_code
            """
        ),
        {
            "old_code": old_code,
            "new_code": new_code,
            "name": name,
            "description": description,
        },
    )


def upgrade() -> None:
    connection = op.get_bind()
    for old_code, new_code, description in PERMISSION_RENAMES:
        _rename_permission(connection, old_code, new_code, description)
    _rename_group(
        connection,
        old_code=GROUP_OLD,
        new_code=GROUP_NEW,
        name=GROUP_NEW_NAME,
        description=GROUP_NEW_DESCRIPTION,
    )


def downgrade() -> None:
    connection = op.get_bind()
    _rename_group(
        connection,
        old_code=GROUP_NEW,
        new_code=GROUP_OLD,
        name=GROUP_OLD_NAME,
        description=GROUP_OLD_DESCRIPTION,
    )
    reverse = (
        ("fair_crm.fair_stand.cost_items.read", "fair_crm.fair_stand.item_prices.read", "Read Fair Stand item prices"),
        ("fair_crm.fair_stand.cost_items.create", "fair_crm.fair_stand.item_prices.create", "Create Fair Stand item prices"),
        ("fair_crm.fair_stand.cost_items.update", "fair_crm.fair_stand.item_prices.update", "Update Fair Stand item prices"),
        ("fair_crm.fair_stand.cost_items.delete", "fair_crm.fair_stand.item_prices.delete", "Delete Fair Stand item prices"),
    )
    for old_code, new_code, description in reverse:
        _rename_permission(connection, old_code, new_code, description)
