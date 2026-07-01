"""Authentication schema hardening for sessions and refresh tokens.

Revision ID: 20260701_0007
Revises: 20260701_0006
Create Date: 2026-07-01

Expands identity_sessions and identity_refresh_tokens for Sprint 0.3.3
authentication domain without data loss.
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0007"
down_revision: Union[str, Sequence[str], None] = "20260701_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SESSIONS_TABLE = "identity_sessions"
REFRESH_TOKENS_TABLE = "identity_refresh_tokens"

INDEX_FAMILY_ID = "ix_identity_refresh_tokens_family_id"
INDEX_ACTIVE_BY_SESSION = "ix_identity_refresh_tokens_active_by_session"
FK_ROTATED_FROM = "fk_identity_refresh_tokens_rotated_from"


def _has_gen_random_uuid(connection: sa.Connection) -> bool:
    if connection.dialect.name != "postgresql":
        return False

    has_builtin = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_proc AS p
                JOIN pg_namespace AS n ON p.pronamespace = n.oid
                WHERE p.proname = 'gen_random_uuid'
                  AND n.nspname = 'pg_catalog'
            )
            """
        )
    ).scalar()
    if has_builtin:
        return True

    return bool(
        connection.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto')")
        ).scalar()
    )


def _backfill_family_ids(connection: sa.Connection) -> None:
    if _has_gen_random_uuid(connection):
        connection.execute(
            sa.text(
                f"""
                UPDATE {REFRESH_TOKENS_TABLE}
                SET family_id = gen_random_uuid()
                WHERE family_id IS NULL
                """
            )
        )
        return

    rows = connection.execute(
        sa.text(f"SELECT id FROM {REFRESH_TOKENS_TABLE} WHERE family_id IS NULL")
    ).fetchall()
    for row in rows:
        connection.execute(
            sa.text(
                f"""
                UPDATE {REFRESH_TOKENS_TABLE}
                SET family_id = :family_id
                WHERE id = :token_id
                """
            ),
            {"family_id": uuid.uuid4(), "token_id": row.id},
        )


def _create_active_by_session_index() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            INDEX_ACTIVE_BY_SESSION,
            REFRESH_TOKENS_TABLE,
            ["session_id", sa.text("created_at DESC")],
            unique=False,
            postgresql_where=sa.text("revoked_at IS NULL AND used_at IS NULL"),
        )
        return

    op.execute(
        sa.text(
            f"""
            CREATE INDEX {INDEX_ACTIVE_BY_SESSION}
            ON {REFRESH_TOKENS_TABLE} (session_id, created_at DESC)
            WHERE revoked_at IS NULL AND used_at IS NULL
            """
        )
    )


def _drop_active_by_session_index() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(INDEX_ACTIVE_BY_SESSION, table_name=REFRESH_TOKENS_TABLE)
        return

    op.execute(sa.text(f"DROP INDEX IF EXISTS {INDEX_ACTIVE_BY_SESSION}"))


def upgrade() -> None:
    # 1. Expand — identity_sessions
    op.add_column(SESSIONS_TABLE, sa.Column("device_name", sa.String(length=128), nullable=True))
    op.add_column(
        SESSIONS_TABLE,
        sa.Column("client_fingerprint", sa.String(length=256), nullable=True),
    )
    op.alter_column(
        SESSIONS_TABLE,
        "last_used_at",
        new_column_name="last_activity_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )

    # 1. Expand — identity_refresh_tokens
    op.add_column(REFRESH_TOKENS_TABLE, sa.Column("family_id", sa.Uuid(), nullable=True))
    op.add_column(REFRESH_TOKENS_TABLE, sa.Column("rotated_from", sa.Uuid(), nullable=True))
    op.add_column(
        REFRESH_TOKENS_TABLE,
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        REFRESH_TOKENS_TABLE,
        sa.Column("revoked_reason", sa.String(length=32), nullable=True),
    )
    op.add_column(
        REFRESH_TOKENS_TABLE,
        sa.Column("reuse_detected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        REFRESH_TOKENS_TABLE,
        sa.Column("created_by_ip", sa.String(length=45), nullable=True),
    )
    op.add_column(
        REFRESH_TOKENS_TABLE,
        sa.Column("created_by_user_agent", sa.String(length=512), nullable=True),
    )

    # 2. Backfill
    connection = op.get_bind()
    _backfill_family_ids(connection)

    # 3. Constraint
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            REFRESH_TOKENS_TABLE,
            "family_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        op.create_foreign_key(
            FK_ROTATED_FROM,
            REFRESH_TOKENS_TABLE,
            REFRESH_TOKENS_TABLE,
            ["rotated_from"],
            ["id"],
            ondelete="SET NULL",
        )
    else:
        with op.batch_alter_table(REFRESH_TOKENS_TABLE) as batch_op:
            batch_op.alter_column("family_id", existing_type=sa.Uuid(), nullable=False)
            batch_op.create_foreign_key(
                FK_ROTATED_FROM,
                REFRESH_TOKENS_TABLE,
                ["rotated_from"],
                ["id"],
                ondelete="SET NULL",
            )

    # 4. Index
    op.create_index(INDEX_FAMILY_ID, REFRESH_TOKENS_TABLE, ["family_id"], unique=False)
    _create_active_by_session_index()


def downgrade() -> None:
    # Reverse index
    _drop_active_by_session_index()
    op.drop_index(INDEX_FAMILY_ID, table_name=REFRESH_TOKENS_TABLE)

    # Reverse constraint
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(FK_ROTATED_FROM, REFRESH_TOKENS_TABLE, type_="foreignkey")
        op.alter_column(
            REFRESH_TOKENS_TABLE,
            "family_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
    else:
        with op.batch_alter_table(REFRESH_TOKENS_TABLE) as batch_op:
            batch_op.drop_constraint(FK_ROTATED_FROM, type_="foreignkey")
            batch_op.alter_column("family_id", existing_type=sa.Uuid(), nullable=True)

    # Reverse expand — identity_refresh_tokens
    op.drop_column(REFRESH_TOKENS_TABLE, "created_by_user_agent")
    op.drop_column(REFRESH_TOKENS_TABLE, "created_by_ip")
    op.drop_column(REFRESH_TOKENS_TABLE, "reuse_detected_at")
    op.drop_column(REFRESH_TOKENS_TABLE, "revoked_reason")
    op.drop_column(REFRESH_TOKENS_TABLE, "used_at")
    op.drop_column(REFRESH_TOKENS_TABLE, "rotated_from")
    op.drop_column(REFRESH_TOKENS_TABLE, "family_id")

    # Reverse expand — identity_sessions
    op.alter_column(
        SESSIONS_TABLE,
        "last_activity_at",
        new_column_name="last_used_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.drop_column(SESSIONS_TABLE, "client_fingerprint")
    op.drop_column(SESSIONS_TABLE, "device_name")
