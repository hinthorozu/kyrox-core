"""Repair OrganizationAdmin organization-scoped permission grants.

Revision ID: 20260817_0059
Revises: 20260817_0058
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260817_0059"
down_revision = "20260817_0058"
branch_labels = None
depends_on = None

ROLE_SLUG = "organization_admin"


def upgrade() -> None:
    connection = op.get_bind()

    # Operations are organization-level CRM capabilities. Repair any stale
    # scope metadata left by historical databases before rebuilding grants.
    connection.execute(
        sa.text(
            """
            UPDATE identity_permissions
            SET permission_scope='organization',
                is_assignable=TRUE,
                updated_at=CURRENT_TIMESTAMP
            WHERE code IN (
                'fair_crm.operations.read',
                'fair_crm.operations.create',
                'fair_crm.operations.update',
                'fair_crm.operations.execute'
            )
            """
        )
    )

    # OrganizationAdmin is the protected full-access organization role. Keep
    # its governance flags normalized and restore every active organization
    # permission idempotently. System-scope permissions remain Super Admin only.
    connection.execute(
        sa.text(
            """
            UPDATE identity_roles
            SET name='OrganizationAdmin',
                scope='organization',
                is_system=TRUE,
                role_kind='protected_global',
                organization_id=NULL,
                permissions_customized=FALSE,
                is_assignable=TRUE,
                is_protected=TRUE,
                auto_include_new_permissions=TRUE,
                updated_at=CURRENT_TIMESTAMP
            WHERE slug=:role_slug
              AND organization_id IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"role_slug": ROLE_SLUG},
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT role.id, permission.id
            FROM identity_roles AS role
            CROSS JOIN identity_permissions AS permission
            WHERE role.slug=:role_slug
              AND role.organization_id IS NULL
              AND role.deleted_at IS NULL
              AND permission.lifecycle_state='active'
              AND permission.permission_scope='organization'
            ON CONFLICT DO NOTHING
            """
        ),
        {"role_slug": ROLE_SLUG},
    )

    # Enforce the organization/system boundary even if an older database had
    # stale grants from before permission_scope existed.
    connection.execute(
        sa.text(
            """
            DELETE FROM identity_role_permissions AS role_permission
            USING identity_roles AS role, identity_permissions AS permission
            WHERE role_permission.role_id=role.id
              AND role_permission.permission_id=permission.id
              AND role.slug=:role_slug
              AND role.organization_id IS NULL
              AND role.deleted_at IS NULL
              AND permission.permission_scope='system'
            """
        ),
        {"role_slug": ROLE_SLUG},
    )


def downgrade() -> None:
    # This migration repairs grants already implied by OrganizationAdmin's
    # contract. Removing those grants on downgrade would destroy valid access.
    pass
