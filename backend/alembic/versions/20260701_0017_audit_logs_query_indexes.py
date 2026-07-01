"""Add composite indexes for organization-scoped audit log queries.

Revision ID: 20260701_0017
Revises: 20260701_0016
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0017"
down_revision: Union[str, Sequence[str], None] = "20260701_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "audit_logs"

INDEXES_TO_DROP = (
    "ix_audit_logs_organization_id",
    "ix_audit_logs_created_at",
    "ix_audit_logs_action",
    "ix_audit_logs_resource_type",
)

COMPOSITE_INDEXES = (
    (
        "ix_audit_logs_org_created_id_desc",
        ["organization_id", "created_at", "id"],
        {"created_at": "DESC", "id": "DESC"},
    ),
    (
        "ix_audit_logs_org_action_created",
        ["organization_id", "action", "created_at"],
        {"created_at": "DESC"},
    ),
    (
        "ix_audit_logs_org_user_created",
        ["organization_id", "user_id", "created_at"],
        {"created_at": "DESC"},
    ),
    (
        "ix_audit_logs_org_resource_type_created",
        ["organization_id", "resource_type", "created_at"],
        {"created_at": "DESC"},
    ),
)


def upgrade() -> None:
    for index_name in INDEXES_TO_DROP:
        op.drop_index(index_name, table_name=TABLE)

    for index_name, columns, postgresql_ops in COMPOSITE_INDEXES:
        op.create_index(
            index_name,
            TABLE,
            columns,
            unique=False,
            postgresql_ops=postgresql_ops,
        )


def downgrade() -> None:
    for index_name, columns, postgresql_ops in reversed(COMPOSITE_INDEXES):
        op.drop_index(index_name, table_name=TABLE)

    op.create_index("ix_audit_logs_organization_id", TABLE, ["organization_id"], unique=False)
    op.create_index("ix_audit_logs_created_at", TABLE, ["created_at"], unique=False)
    op.create_index("ix_audit_logs_action", TABLE, ["action"], unique=False)
    op.create_index("ix_audit_logs_resource_type", TABLE, ["resource_type"], unique=False)
