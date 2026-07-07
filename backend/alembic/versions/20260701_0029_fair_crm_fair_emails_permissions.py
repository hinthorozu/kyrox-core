"""Seed fair_crm.fair_emails.* permissions for FAIR CRM product integration.

Revision ID: 20260701_0029
Revises: 20260701_0028
Create Date: 2026-07-05
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0029"
down_revision: Union[str, Sequence[str], None] = "20260701_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROUPS_TABLE = "identity_permission_groups"
PERMISSIONS_TABLE = "identity_permissions"
FAIR_CRM_MODULE = "fair_crm"

PERMISSION_GROUP = {
    "code": "fair_crm.fair_emails",
    "name": "FAIR CRM Fair Emails",
    "description": "FAIR CRM fair bulk email permissions",
    "sort_order": 86,
}

PERMISSION_CODES: tuple[tuple[str, str], ...] = (
    ("fair_crm.fair_emails.preview", "Preview fair bulk email recipients and content"),
    ("fair_crm.fair_emails.send", "Send fair bulk email campaigns"),
)

ALL_NEW_PERMISSION_CODES: tuple[str, ...] = tuple(code for code, _ in PERMISSION_CODES)


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
    group_id = _ensure_permission_group(
        connection,
        code=PERMISSION_GROUP["code"],
        name=PERMISSION_GROUP["name"],
        description=PERMISSION_GROUP["description"],
        sort_order=PERMISSION_GROUP["sort_order"],
    )
    for code, description in PERMISSION_CODES:
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

    connection.execute(
        sa.text(f"DELETE FROM {GROUPS_TABLE} WHERE code = :code"),
        {"code": PERMISSION_GROUP["code"]},
    )
