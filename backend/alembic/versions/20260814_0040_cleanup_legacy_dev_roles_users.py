"""Remove legacy Fair CRM dev users and deprecated organization roles.

Revision ID: 20260814_0040
Revises: 20260814_0039
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260814_0040"
down_revision = "20260814_0039"
branch_labels = None
depends_on = None

LEGACY_DEV_EMAILS = (
    "dev-admin@example.com",
    "dev-manager@example.com",
    "dev-sales@example.com",
    "dev-viewer@example.com",
    "dev-scraper@example.com",
)

DEPRECATED_ROLE_SLUGS = (
    "admin",
    "manager",
    "sales",
    "viewer",
    "scraper_operator",
    "member",
)


def upgrade() -> None:
    bind = op.get_bind()

    # These are historical Fair CRM bootstrap users only. Because all identity
    # foreign keys now use ON DELETE CASCADE, memberships and role assignments
    # are removed automatically with the user rows.
    bind.execute(
        sa.text("DELETE FROM identity_users WHERE email IN :emails").bindparams(
            sa.bindparam("emails", expanding=True)
        ),
        {"emails": list(LEGACY_DEV_EMAILS)},
    )

    # Keep only the two canonical organization role templates: owner and
    # organization_admin. Cascades remove stale organization-role bindings and
    # role-permission mappings for these deprecated templates.
    bind.execute(
        sa.text(
            """
            DELETE FROM identity_roles
            WHERE scope = 'organization'
              AND slug IN :slugs
            """
        ).bindparams(sa.bindparam("slugs", expanding=True)),
        {"slugs": list(DEPRECATED_ROLE_SLUGS)},
    )


def downgrade() -> None:
    # Removed users contained password hashes and historical assignments that
    # cannot be reconstructed safely. The seed can recreate canonical data.
    raise RuntimeError("20260814_0040 is an irreversible identity cleanup migration")
