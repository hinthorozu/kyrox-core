"""Add group_id to identity_permissions and remove module column.

Revision ID: 20260701_0009
Revises: 20260701_0008
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0009"
down_revision: Union[str, Sequence[str], None] = "20260701_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS_TABLE = "identity_permissions"
GROUPS_TABLE = "identity_permission_groups"
FK_GROUP_ID = "fk_identity_permissions_group_id"
IX_GROUP_ID = "ix_identity_permissions_group_id"


def _backfill_group_ids(connection: sa.Connection) -> None:
    connection.execute(
        sa.text(
            f"""
            UPDATE {PERMISSIONS_TABLE}
            SET group_id = (
                SELECT g.id
                FROM {GROUPS_TABLE} AS g
                WHERE g.module = {PERMISSIONS_TABLE}.module
                ORDER BY g.sort_order
                LIMIT 1
            )
            WHERE group_id IS NULL
            """
        )
    )


def upgrade() -> None:
    op.add_column(
        PERMISSIONS_TABLE,
        sa.Column("group_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    connection = op.get_bind()
    _backfill_group_ids(connection)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(PERMISSIONS_TABLE, "group_id", nullable=False)
        op.create_foreign_key(
            FK_GROUP_ID,
            PERMISSIONS_TABLE,
            GROUPS_TABLE,
            ["group_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(IX_GROUP_ID, PERMISSIONS_TABLE, ["group_id"], unique=False)
        op.drop_column(PERMISSIONS_TABLE, "module")
        return

    with op.batch_alter_table(PERMISSIONS_TABLE) as batch_op:
        batch_op.alter_column("group_id", existing_type=sa.Uuid(as_uuid=True), nullable=False)
        batch_op.create_foreign_key(
            FK_GROUP_ID,
            GROUPS_TABLE,
            ["group_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(IX_GROUP_ID, ["group_id"], unique=False)
        batch_op.drop_column("module")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.add_column(
            PERMISSIONS_TABLE,
            sa.Column("module", sa.String(length=64), nullable=True),
        )
        connection = op.get_bind()
        connection.execute(
            sa.text(
                f"""
                UPDATE {PERMISSIONS_TABLE} AS p
                SET module = (
                    SELECT g.module
                    FROM {GROUPS_TABLE} AS g
                    WHERE g.id = p.group_id
                )
                """
            )
        )
        op.alter_column(PERMISSIONS_TABLE, "module", nullable=False)
        op.drop_index(IX_GROUP_ID, table_name=PERMISSIONS_TABLE)
        op.drop_constraint(FK_GROUP_ID, PERMISSIONS_TABLE, type_="foreignkey")
        op.drop_column(PERMISSIONS_TABLE, "group_id")
        return

    with op.batch_alter_table(PERMISSIONS_TABLE) as batch_op:
        batch_op.add_column(sa.Column("module", sa.String(length=64), nullable=True))

    connection = op.get_bind()
    connection.execute(
        sa.text(
            f"""
            UPDATE {PERMISSIONS_TABLE} AS p
            SET module = (
                SELECT g.module
                FROM {GROUPS_TABLE} AS g
                WHERE g.id = p.group_id
            )
            """
        )
    )

    with op.batch_alter_table(PERMISSIONS_TABLE) as batch_op:
        batch_op.alter_column("module", existing_type=sa.String(length=64), nullable=False)
        batch_op.drop_index(IX_GROUP_ID)
        batch_op.drop_constraint(FK_GROUP_ID, type_="foreignkey")
        batch_op.drop_column("group_id")
