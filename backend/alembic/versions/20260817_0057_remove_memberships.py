"""Replace memberships with direct user organization ownership.

Revision ID: 20260817_0057
Revises: 20260817_0056
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260817_0057"
down_revision = "20260817_0056"
branch_labels = None
depends_on = None

USERS = "identity_users"
ORGANIZATIONS = "identity_organizations"
USER_ROLES = "identity_user_roles"
MEMBERSHIPS = "identity_memberships"
INVITES = "identity_membership_invites"
USER_ORG_INDEX = "ix_identity_users_organization_id"
USER_ORG_FK = "fk_identity_users_organization_id"


def _table_exists(connection: sa.Connection, table_name: str) -> bool:
    return sa.inspect(connection).has_table(table_name)


def _backfill_user_organizations(connection: sa.Connection) -> None:
    # Active role assignments are the strongest legacy source of truth. If old
    # data contains multiple active organization roles, the most recently
    # assigned role wins and the other active assignments are revoked below.
    connection.execute(
        sa.text(
            f"""
            UPDATE {USERS} AS u
            SET organization_id = (
                SELECT ur.organization_id
                FROM {USER_ROLES} AS ur
                WHERE ur.user_id = u.id
                  AND ur.status = 'active'
                  AND ur.revoked_at IS NULL
                ORDER BY ur.assigned_at DESC
                LIMIT 1
            )
            WHERE u.is_super_admin = FALSE
              AND EXISTS (
                SELECT 1
                FROM {USER_ROLES} AS ur
                WHERE ur.user_id = u.id
                  AND ur.status = 'active'
                  AND ur.revoked_at IS NULL
              )
            """
        )
    )

    # Membership is only a fallback for legacy users that do not have an
    # active role assignment. Prefer active memberships, then the latest row.
    connection.execute(
        sa.text(
            f"""
            UPDATE {USERS} AS u
            SET organization_id = (
                SELECT m.organization_id
                FROM {MEMBERSHIPS} AS m
                WHERE m.user_id = u.id
                  AND m.deleted_at IS NULL
                ORDER BY
                    CASE WHEN m.status = 'active' THEN 0 ELSE 1 END,
                    m.updated_at DESC
                LIMIT 1
            )
            WHERE u.is_super_admin = FALSE
              AND u.organization_id IS NULL
              AND EXISTS (
                SELECT 1
                FROM {MEMBERSHIPS} AS m
                WHERE m.user_id = u.id
                  AND m.deleted_at IS NULL
              )
            """
        )
    )

    # Super Admin is platform-wide and never belongs to an organization.
    connection.execute(
        sa.text(f"UPDATE {USERS} SET organization_id=NULL WHERE is_super_admin=TRUE")
    )

    # The new model permits exactly one organization per normal user. Retain
    # only active role assignments for the organization selected above.
    connection.execute(
        sa.text(
            f"""
            UPDATE {USER_ROLES} AS ur
            SET status='revoked', revoked_at=CURRENT_TIMESTAMP
            WHERE ur.status='active'
              AND ur.revoked_at IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM {USERS} AS u
                  WHERE u.id=ur.user_id
                    AND u.is_super_admin=FALSE
                    AND u.organization_id IS NOT NULL
                    AND u.organization_id <> ur.organization_id
              )
            """
        )
    )


def _remove_membership_permissions(connection: sa.Connection) -> None:
    permission_filter = (
        "code LIKE 'identity.membership.%' "
        "OR code LIKE 'identity.memberships.%'"
    )
    for table_name in (
        "identity_role_template_exclusions",
        "identity_role_permissions",
    ):
        if _table_exists(connection, table_name):
            connection.execute(
                sa.text(
                    f"""
                    DELETE FROM {table_name}
                    WHERE permission_id IN (
                        SELECT id FROM identity_permissions
                        WHERE {permission_filter}
                    )
                    """
                )
            )
    connection.execute(
        sa.text(
            f"""
            DELETE FROM identity_permissions
            WHERE {permission_filter}
            """
        )
    )


def upgrade() -> None:
    connection = op.get_bind()

    op.add_column(
        USERS,
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        USER_ORG_FK,
        USERS,
        ORGANIZATIONS,
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )
    op.create_index(USER_ORG_INDEX, USERS, ["organization_id"], unique=False)

    if _table_exists(connection, MEMBERSHIPS):
        _backfill_user_organizations(connection)

    _remove_membership_permissions(connection)

    if _table_exists(connection, INVITES):
        op.drop_table(INVITES)
    if _table_exists(connection, MEMBERSHIPS):
        op.drop_table(MEMBERSHIPS)


def downgrade() -> None:
    connection = op.get_bind()

    op.create_table(
        MEMBERSHIPS,
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], [f"{USERS}.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], [f"{ORGANIZATIONS}.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_identity_memberships_user_organization"),
    )
    op.create_index("ix_identity_memberships_user_id", MEMBERSHIPS, ["user_id"], unique=False)
    op.create_index("ix_identity_memberships_organization_id", MEMBERSHIPS, ["organization_id"], unique=False)
    op.create_index("ix_identity_memberships_org_effective", MEMBERSHIPS, ["organization_id", "status"], unique=False)

    rows = connection.execute(
        sa.text(
            f"""
            SELECT id, organization_id
            FROM {USERS}
            WHERE organization_id IS NOT NULL
              AND deleted_at IS NULL
            """
        )
    ).mappings().all()
    for row in rows:
        connection.execute(
            sa.text(
                f"""
                INSERT INTO {MEMBERSHIPS}
                    (id, user_id, organization_id, status, invited_at, joined_at,
                     created_at, updated_at, deleted_at)
                VALUES
                    (:id, :user_id, :organization_id, 'active', NULL,
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": str(row["id"]),
                "organization_id": str(row["organization_id"]),
            },
        )

    op.create_table(
        INVITES,
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], [f"{ORGANIZATIONS}.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], [f"{USERS}.id"], ondelete="CASCADE", onupdate="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_identity_membership_invites_token_hash"),
    )
    op.create_index(
        "ix_identity_membership_invites_organization_id",
        INVITES,
        ["organization_id"],
        unique=False,
    )

    op.drop_index(USER_ORG_INDEX, table_name=USERS)
    op.drop_constraint(USER_ORG_FK, USERS, type_="foreignkey")
    op.drop_column(USERS, "organization_id")
