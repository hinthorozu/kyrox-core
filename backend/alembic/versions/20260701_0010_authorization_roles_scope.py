"""Add scope to identity_roles and remove organization_id.

Revision ID: 20260701_0010
Revises: 20260701_0009
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0010"
down_revision: Union[str, Sequence[str], None] = "20260701_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLES_TABLE = "identity_roles"
ORG_ROLES_TABLE = "identity_organization_roles"
UQ_ORG_SLUG = "uq_identity_roles_organization_slug"
IX_ORGANIZATION_ID = "ix_identity_roles_organization_id"
UQ_SCOPE_SLUG = "uq_identity_roles_scope_slug"
IX_SCOPE = "ix_identity_roles_scope"
FK_ORGANIZATION = "fk_identity_roles_organization_id"


def _drop_org_slug_unique(batch_op: object | None = None) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for unique in inspector.get_unique_constraints(ROLES_TABLE):
        if set(unique.get("column_names", [])) == {"organization_id", "slug"}:
            constraint_name = unique.get("name")
            if constraint_name is None:
                return
            if batch_op is None:
                op.drop_constraint(constraint_name, ROLES_TABLE, type_="unique")
            else:
                batch_op.drop_constraint(constraint_name, type_="unique")
            return


def _drop_organization_fk(batch_op: object | None = None) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(ROLES_TABLE):
        if "organization_id" in fk.get("constrained_columns", []):
            if batch_op is None:
                op.drop_constraint(fk["name"], ROLES_TABLE, type_="foreignkey")
            else:
                batch_op.drop_constraint(fk["name"], type_="foreignkey")
            return


def upgrade() -> None:
    op.add_column(
        ROLES_TABLE,
        sa.Column("scope", sa.String(length=32), nullable=True),
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            f"""
            UPDATE {ROLES_TABLE}
            SET scope = CASE
                WHEN organization_id IS NOT NULL THEN 'organization'
                ELSE 'platform'
            END
            WHERE scope IS NULL
            """
        )
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(ROLES_TABLE, "scope", nullable=False)
        op.drop_index(IX_ORGANIZATION_ID, table_name=ROLES_TABLE)
        _drop_org_slug_unique()
        _drop_organization_fk()
        op.drop_column(ROLES_TABLE, "organization_id")
        op.create_unique_constraint(UQ_SCOPE_SLUG, ROLES_TABLE, ["scope", "slug"])
        op.create_index(IX_SCOPE, ROLES_TABLE, ["scope"], unique=False)
        return

    with op.batch_alter_table(ROLES_TABLE) as batch_op:
        batch_op.alter_column("scope", existing_type=sa.String(length=32), nullable=False)
        batch_op.drop_index(IX_ORGANIZATION_ID)
        _drop_org_slug_unique(batch_op)
        _drop_organization_fk(batch_op)
        batch_op.drop_column("organization_id")
        batch_op.create_unique_constraint(UQ_SCOPE_SLUG, ["scope", "slug"])
        batch_op.create_index(IX_SCOPE, ["scope"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(IX_SCOPE, table_name=ROLES_TABLE)
        op.drop_constraint(UQ_SCOPE_SLUG, ROLES_TABLE, type_="unique")
        op.add_column(
            ROLES_TABLE,
            sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True),
        )
        connection = op.get_bind()
        inspector = sa.inspect(connection)
        if ORG_ROLES_TABLE in inspector.get_table_names():
            connection.execute(
                sa.text(
                    f"""
                    UPDATE {ROLES_TABLE} AS r
                    SET organization_id = (
                        SELECT orr.organization_id
                        FROM {ORG_ROLES_TABLE} AS orr
                        WHERE orr.role_id = r.id
                          AND orr.deleted_at IS NULL
                        ORDER BY orr.created_at
                        LIMIT 1
                    )
                    """
                )
            )
        op.create_foreign_key(
            FK_ORGANIZATION,
            ROLES_TABLE,
            "identity_organizations",
            ["organization_id"],
            ["id"],
        )
        op.create_unique_constraint(UQ_ORG_SLUG, ROLES_TABLE, ["organization_id", "slug"])
        op.create_index(IX_ORGANIZATION_ID, ROLES_TABLE, ["organization_id"], unique=False)
        op.drop_column(ROLES_TABLE, "scope")
        return

    with op.batch_alter_table(ROLES_TABLE) as batch_op:
        batch_op.drop_index(IX_SCOPE)
        batch_op.drop_constraint(UQ_SCOPE_SLUG, type_="unique")
        batch_op.add_column(sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.drop_column("scope")

    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if ORG_ROLES_TABLE in inspector.get_table_names():
        connection.execute(
            sa.text(
                f"""
                UPDATE {ROLES_TABLE} AS r
                SET organization_id = (
                    SELECT orr.organization_id
                    FROM {ORG_ROLES_TABLE} AS orr
                    WHERE orr.role_id = r.id
                      AND orr.deleted_at IS NULL
                    ORDER BY orr.created_at
                    LIMIT 1
                )
                """
            )
        )

    with op.batch_alter_table(ROLES_TABLE) as batch_op:
        batch_op.create_foreign_key(
            FK_ORGANIZATION,
            "identity_organizations",
            ["organization_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(UQ_ORG_SLUG, ["organization_id", "slug"])
        batch_op.create_index(IX_ORGANIZATION_ID, ["organization_id"], unique=False)