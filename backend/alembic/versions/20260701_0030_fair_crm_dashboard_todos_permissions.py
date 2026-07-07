"""Seed fair_crm.dashboard.* and fair_crm.todos.* permissions for FAIR CRM integration.

Revision ID: 20260701_0030
Revises: 20260701_0029
Create Date: 2026-07-07
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0030"
down_revision: Union[str, Sequence[str], None] = "20260701_0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROUPS_TABLE = "identity_permission_groups"
PERMISSIONS_TABLE = "identity_permissions"
FAIR_CRM_MODULE = "fair_crm"

PERMISSION_GROUPS: tuple[dict, ...] = (
    {
        "code": "fair_crm.dashboard",
        "name": "FAIR CRM Dashboard",
        "description": "FAIR CRM dashboard permissions",
        "sort_order": 87,
        "permissions": (
            ("fair_crm.dashboard.read", "Read CRM dashboard"),
        ),
    },
    {
        "code": "fair_crm.todos",
        "name": "FAIR CRM Todos",
        "description": "FAIR CRM todo permissions",
        "sort_order": 88,
        "permissions": (
            ("fair_crm.todos.read", "Read CRM todos"),
            ("fair_crm.todos.create", "Create CRM todos"),
            ("fair_crm.todos.update", "Update CRM todos"),
            ("fair_crm.todos.archive", "Archive CRM todos"),
            ("fair_crm.todos.delete", "Delete CRM todos"),
        ),
    },
    {
        "code": "fair_crm.todos.outcomes",
        "name": "FAIR CRM Todo Outcomes",
        "description": "FAIR CRM todo outcome permissions",
        "sort_order": 89,
        "permissions": (
            ("fair_crm.todos.outcomes.read", "Read CRM todo outcomes"),
            ("fair_crm.todos.outcomes.create", "Create CRM todo outcomes"),
            ("fair_crm.todos.outcomes.update", "Update CRM todo outcomes"),
            ("fair_crm.todos.outcomes.deactivate", "Deactivate CRM todo outcomes"),
        ),
    },
)

ALL_NEW_PERMISSION_CODES: tuple[str, ...] = tuple(
    code for group in PERMISSION_GROUPS for code, _ in group["permissions"]
)


def _ensure_permission_group(
    connection: sa.Connection,
    *,
    code: str,
    name: str,
    description: str,
    sort_order: int,
) -> uuid.UUID:
    group_id = connection.execute(
        sa.text(
            f"""
            SELECT id FROM {GROUPS_TABLE}
            WHERE code = :code
            LIMIT 1
            """
        ),
        {"code": code},
    ).scalar()

    if group_id is not None:
        return uuid.UUID(str(group_id))

    group_id = uuid.uuid4()
    connection.execute(
        sa.text(
            f"""
            INSERT INTO {GROUPS_TABLE} (
                id, code, name, module, description, sort_order, is_system, created_at, updated_at
            ) VALUES (
                :id, :code, :name, :module, :description, :sort_order, :is_system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "id": str(group_id),
            "code": code,
            "name": name,
            "module": FAIR_CRM_MODULE,
            "description": description,
            "sort_order": sort_order,
            "is_system": True,
        },
    )
    return group_id


def _ensure_permission(
    connection: sa.Connection,
    *,
    group_id: uuid.UUID,
    code: str,
    description: str,
) -> None:
    connection.execute(
        sa.text(
            f"""
            INSERT INTO {PERMISSIONS_TABLE} (
                id, group_id, code, description, is_system, created_at, updated_at
            )
            SELECT :id, :group_id, :code, :description, :is_system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (
                SELECT 1 FROM {PERMISSIONS_TABLE} WHERE code = :code
            )
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "group_id": str(group_id),
            "code": code,
            "description": description,
            "is_system": True,
        },
    )


def upgrade() -> None:
    connection = op.get_bind()
    for group in PERMISSION_GROUPS:
        group_id = _ensure_permission_group(
            connection,
            code=group["code"],
            name=group["name"],
            description=group["description"],
            sort_order=group["sort_order"],
        )
        for code, description in group["permissions"]:
            _ensure_permission(
                connection,
                group_id=group_id,
                code=code,
                description=description,
            )


def downgrade() -> None:
    connection = op.get_bind()
    for code in ALL_NEW_PERMISSION_CODES:
        connection.execute(
            sa.text(f"DELETE FROM {PERMISSIONS_TABLE} WHERE code = :code"),
            {"code": code},
        )

    for group in PERMISSION_GROUPS:
        connection.execute(
            sa.text(f"DELETE FROM {GROUPS_TABLE} WHERE code = :code"),
            {"code": group["code"]},
        )
