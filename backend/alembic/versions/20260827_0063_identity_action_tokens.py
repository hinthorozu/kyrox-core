"""Add one-time identity action tokens.

Revision ID: 20260827_0063
Revises: 20260821_0062
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260827_0063"
down_revision = "20260821_0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_action_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity_users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_identity_action_tokens_token_hash",
        ),
    )
    op.create_index(
        "ix_identity_action_tokens_user_purpose",
        "identity_action_tokens",
        ["user_id", "purpose"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_action_tokens_user_purpose",
        table_name="identity_action_tokens",
    )
    op.drop_table("identity_action_tokens")
