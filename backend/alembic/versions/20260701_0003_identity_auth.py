"""Identity session and refresh token tables.

Revision ID: 20260701_0003
Revises: 20260701_0002
Create Date: 2026-07-01

Creates identity_sessions and identity_refresh_tokens for authentication core.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0003"
down_revision: Union[str, Sequence[str], None] = "20260701_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identity_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_identity_sessions_user_id", "identity_sessions", ["user_id"], unique=False)

    op.create_table(
        "identity_refresh_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["session_id"], ["identity_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_identity_refresh_tokens_token_hash"),
    )
    op.create_index(
        "ix_identity_refresh_tokens_session_id",
        "identity_refresh_tokens",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_identity_refresh_tokens_session_id", table_name="identity_refresh_tokens")
    op.drop_table("identity_refresh_tokens")

    op.drop_index("ix_identity_sessions_user_id", table_name="identity_sessions")
    op.drop_table("identity_sessions")
