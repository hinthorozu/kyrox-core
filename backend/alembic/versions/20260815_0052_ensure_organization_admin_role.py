"""Ensure the protected OrganizationAdmin role exists on every database.

Revision ID: 20260815_0052
Revises: 20260815_0051
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260815_0052"
down_revision = "20260815_0051"
branch_labels = None
depends_on = None

ROLE_SLUG = "organization_admin"
ROLE_NAME = "OrganizationAdmin"


def upgrade() -> None:
    connection = op.get_bind()

    role_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM identity_roles
            WHERE scope = 'organization'
              AND slug = :slug
              AND organization_id IS NULL
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"slug": ROLE_SLUG},
    ).scalar()

    if role_id is None:
        role_id = uuid.uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_roles (
                    id,
                    name,
                    slug,
                    scope,
                    is_system,
                    role_kind,
                    organization_id,
                    source_template_role_id,
                    template_version,
                    source_template_version,
                    permissions_customized,
                    is_assignable,
                    is_protected,
                    auto_include_new_permissions,
                    created_at,
                    updated_at,
                    deleted_at
                ) VALUES (
                    :id,
                    :name,
                    :slug,
                    'organization',
                    TRUE,
                    'protected_global',
                    NULL,
                    NULL,
                    1,
                    NULL,
                    FALSE,
                    TRUE,
                    TRUE,
                    TRUE,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    NULL
                )
                """
            ),
            {
                "id": str(role_id),
                "name": ROLE_NAME,
                "slug": ROLE_SLUG,
            },
        )
    else:
        connection.execute(
            sa.text(
                """
                UPDATE identity_roles
                SET name = :name,
                    scope = 'organization',
                    is_system = TRUE,
                    role_kind = 'protected_global',
                    organization_id = NULL,
                    permissions_customized = FALSE,
                    is_assignable = TRUE,
                    is_protected = TRUE,
                    auto_include_new_permissions = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {"id": str(role_id), "name": ROLE_NAME},
        )

    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT :role_id, p.id
            FROM identity_permissions AS p
            WHERE p.lifecycle_state = 'active'
            ON CONFLICT DO NOTHING
            """
        ),
        {"role_id": str(role_id)},
    )


def downgrade() -> None:
    # Do not remove the protected role on downgrade. It may predate this repair
    # migration and can be referenced by organization role assignments.
    pass
