"""Create identity_membership_invites table.

Revision ID: 20260701_0015
Revises: 20260701_0014
Create Date: 2026-07-01

Adds invite persistence for Sprint 0.3.5 membership flow.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0015"
down_revision: Union[str, Sequence[str], None] = "20260701_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INVITES_TABLE = "identity_membership_invites"
ORGANIZATIONS_TABLE = "identity_organizations"
USERS_TABLE = "identity_users"

INDEX_ORGANIZATION_ID = "ix_identity_membership_invites_organization_id"
INDEX_PENDING_BY_ORG = "ix_identity_membership_invites_pending_by_org"
UQ_TOKEN_HASH = "uq_identity_membership_invites_token_hash"


def _create_pending_by_org_index() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            INDEX_PENDING_BY_ORG,
            INVITES_TABLE,
            ["organization_id"],
            unique=False,
            postgresql_where=sa.text("accepted_at IS NULL AND revoked_at IS NULL"),
        )
        return

    op.execute(
        sa.text(
            f"""
            CREATE INDEX {INDEX_PENDING_BY_ORG}
            ON {INVITES_TABLE} (organization_id)
            WHERE accepted_at IS NULL AND revoked_at IS NULL
            """
        )
    )


def _drop_pending_by_org_index() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(INDEX_PENDING_BY_ORG, table_name=INVITES_TABLE)
        return

    op.execute(sa.text(f"DROP INDEX IF EXISTS {INDEX_PENDING_BY_ORG}"))


def upgrade() -> None:
    op.create_table(
        INVITES_TABLE,
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            [f"{ORGANIZATIONS_TABLE}.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            [f"{USERS_TABLE}.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name=UQ_TOKEN_HASH),
    )
    op.create_index(
        INDEX_ORGANIZATION_ID,
        INVITES_TABLE,
        ["organization_id"],
        unique=False,
    )
    _create_pending_by_org_index()


def downgrade() -> None:
    _drop_pending_by_org_index()
    op.drop_index(INDEX_ORGANIZATION_ID, table_name=INVITES_TABLE)
    op.drop_table(INVITES_TABLE)
