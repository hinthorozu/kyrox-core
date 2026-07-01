"""Membership schema cleanup and performance indexes.

Revision ID: 20260701_0016
Revises: 20260701_0015
Create Date: 2026-07-01

Drops deprecated identity_memberships.role_id and adds effective-membership indexes.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0016"
down_revision: Union[str, Sequence[str], None] = "20260701_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEMBERSHIPS_TABLE = "identity_memberships"
ROLES_TABLE = "identity_roles"
USER_ROLES_TABLE = "identity_user_roles"

INDEX_ROLE_ID = "ix_identity_memberships_role_id"
FK_ROLE_ID = "fk_identity_memberships_role_id"
INDEX_ORG_EFFECTIVE = "ix_identity_memberships_org_effective"


def _column_exists(connection: sa.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(connection)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(connection: sa.Connection, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(connection)
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _fk_exists(connection: sa.Connection, table_name: str, fk_name: str) -> bool:
    inspector = sa.inspect(connection)
    return fk_name in {fk["name"] for fk in inspector.get_foreign_keys(table_name)}


def _assert_role_id_migration_complete(connection: sa.Connection) -> None:
    orphan_count = connection.execute(
        sa.text(
            f"""
            SELECT COUNT(*)
            FROM {MEMBERSHIPS_TABLE} AS m
            WHERE m.role_id IS NOT NULL
              AND m.deleted_at IS NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {USER_ROLES_TABLE} AS ur
                WHERE ur.user_id = m.user_id
                  AND ur.organization_id = m.organization_id
                  AND ur.status = 'active'
              )
            """
        )
    ).scalar_one()

    if orphan_count > 0:
        raise RuntimeError(
            "Cannot drop identity_memberships.role_id: "
            f"{orphan_count} active membership(s) have role_id without a matching "
            "active identity_user_roles row."
        )


def _drop_role_id_column(connection: sa.Connection) -> None:
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(MEMBERSHIPS_TABLE) as batch_op:
            if _index_exists(connection, MEMBERSHIPS_TABLE, INDEX_ROLE_ID):
                batch_op.drop_index(INDEX_ROLE_ID)
            if _fk_exists(connection, MEMBERSHIPS_TABLE, FK_ROLE_ID):
                batch_op.drop_constraint(FK_ROLE_ID, type_="foreignkey")
            batch_op.drop_column("role_id")
        return

    if _index_exists(connection, MEMBERSHIPS_TABLE, INDEX_ROLE_ID):
        op.drop_index(INDEX_ROLE_ID, table_name=MEMBERSHIPS_TABLE)

    if _fk_exists(connection, MEMBERSHIPS_TABLE, FK_ROLE_ID):
        op.drop_constraint(FK_ROLE_ID, MEMBERSHIPS_TABLE, type_="foreignkey")

    op.drop_column(MEMBERSHIPS_TABLE, "role_id")


def _create_org_effective_index() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            INDEX_ORG_EFFECTIVE,
            MEMBERSHIPS_TABLE,
            ["organization_id", "status"],
            unique=False,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )
        return

    op.execute(
        sa.text(
            f"""
            CREATE INDEX {INDEX_ORG_EFFECTIVE}
            ON {MEMBERSHIPS_TABLE} (organization_id, status)
            WHERE deleted_at IS NULL
            """
        )
    )


def _drop_org_effective_index() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(INDEX_ORG_EFFECTIVE, table_name=MEMBERSHIPS_TABLE)
        return

    op.execute(sa.text(f"DROP INDEX IF EXISTS {INDEX_ORG_EFFECTIVE}"))


def _restore_role_id_column() -> None:
    bind = op.get_bind()
    connection = op.get_bind()

    if _column_exists(connection, MEMBERSHIPS_TABLE, "role_id"):
        return

    op.add_column(
        MEMBERSHIPS_TABLE,
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=True),
    )

    if bind.dialect.name == "postgresql":
        op.create_foreign_key(
            FK_ROLE_ID,
            MEMBERSHIPS_TABLE,
            ROLES_TABLE,
            ["role_id"],
            ["id"],
        )
    else:
        with op.batch_alter_table(MEMBERSHIPS_TABLE) as batch_op:
            batch_op.create_foreign_key(
                FK_ROLE_ID,
                ROLES_TABLE,
                ["role_id"],
                ["id"],
            )

    op.create_index(
        INDEX_ROLE_ID,
        MEMBERSHIPS_TABLE,
        ["role_id"],
        unique=False,
    )


def upgrade() -> None:
    connection = op.get_bind()

    if _column_exists(connection, MEMBERSHIPS_TABLE, "role_id"):
        _assert_role_id_migration_complete(connection)
        _drop_role_id_column(connection)

    _create_org_effective_index()


def downgrade() -> None:
    _drop_org_effective_index()
    _restore_role_id_column()
