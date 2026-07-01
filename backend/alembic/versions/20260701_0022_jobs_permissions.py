"""Seed jobs.platform.enqueue and jobs.platform.read permissions for jobs API.

Revision ID: 20260701_0022
Revises: 20260701_0021
Create Date: 2026-07-01
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0022"
down_revision: Union[str, Sequence[str], None] = "20260701_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROUPS_TABLE = "identity_permission_groups"
PERMISSIONS_TABLE = "identity_permissions"
PERMISSION_CODES = (
    ("jobs.platform.enqueue", "Enqueue organization background jobs"),
    ("jobs.platform.read", "Read background job status"),
)


def upgrade() -> None:
    connection = op.get_bind()
    group_id = connection.execute(
        sa.text(
            f"""
            SELECT id FROM {GROUPS_TABLE}
            WHERE module = :module
            LIMIT 1
            """
        ),
        {"module": "jobs"},
    ).scalar()

    if group_id is None:
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
                "code": "jobs.platform",
                "name": "Platform Jobs",
                "module": "jobs",
                "description": "Platform background job permissions",
                "sort_order": 10,
                "is_system": True,
            },
        )

    for code, description in PERMISSION_CODES:
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


def downgrade() -> None:
    connection = op.get_bind()
    for code, _ in PERMISSION_CODES:
        connection.execute(
            sa.text(f"DELETE FROM {PERMISSIONS_TABLE} WHERE code = :code"),
            {"code": code},
        )
