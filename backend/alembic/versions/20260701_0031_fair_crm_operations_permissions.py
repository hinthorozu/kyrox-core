"""Seed fair_crm.operations.* permissions for FAIR CRM Operation Engine.

Revision ID: 20260701_0031
Revises: 20260701_0030
Create Date: 2026-07-22
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0031"
down_revision: Union[str, Sequence[str], None] = "20260701_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROUPS_TABLE = "identity_permission_groups"
PERMISSIONS_TABLE = "identity_permissions"
FAIR_CRM_MODULE = "fair_crm"

PERMISSION_GROUPS: tuple[dict, ...] = (
    {
        "code": "fair_crm.operations",
        "name": "FAIR CRM Operations",
        "description": "FAIR CRM Operation Engine permissions",
        "sort_order": 90,
        "permissions": (
            ("fair_crm.operations.read", "Read CRM operations"),
            ("fair_crm.operations.create", "Create CRM operations"),
            ("fair_crm.operations.update", "Update CRM operations"),
            ("fair_crm.operations.execute", "Start/cancel/retry CRM operations"),
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
