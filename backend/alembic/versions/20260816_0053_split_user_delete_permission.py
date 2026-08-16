"""Split organization user deletion into a dedicated permission.

Revision ID: 20260816_0053
Revises: 20260815_0052
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "20260816_0053"
down_revision = "20260815_0052"
branch_labels = None
depends_on = None

UPDATE_CODE = "identity.users.update"
DELETE_CODE = "identity.users.delete"
UPDATE_DESCRIPTION = "Update organization users"
LEGACY_UPDATE_DESCRIPTION = "Update and remove organization users"
DELETE_DESCRIPTION = "Delete organization users"


def _permission_id(connection, code: str):
    return connection.execute(
        sa.text("SELECT id FROM identity_permissions WHERE code=:code"),
        {"code": code},
    ).scalar_one_or_none()


def upgrade() -> None:
    connection = op.get_bind()
    update_id = _permission_id(connection, UPDATE_CODE)
    if update_id is None:
        raise RuntimeError(f"Required permission is missing: {UPDATE_CODE}")

    connection.execute(
        sa.text(
            """
            UPDATE identity_permissions
            SET description=:description, updated_at=CURRENT_TIMESTAMP
            WHERE id=:permission_id
            """
        ),
        {"permission_id": update_id, "description": UPDATE_DESCRIPTION},
    )

    delete_id = _permission_id(connection, DELETE_CODE)
    if delete_id is None:
        source = connection.execute(
            sa.text(
                """
                SELECT group_id, is_system, lifecycle_state, is_assignable
                FROM identity_permissions
                WHERE id=:permission_id
                """
            ),
            {"permission_id": update_id},
        ).mappings().one()
        delete_id = uuid.uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_permissions (
                    id, group_id, code, description, is_system,
                    lifecycle_state, is_assignable, created_at, updated_at
                ) VALUES (
                    :id, :group_id, :code, :description, :is_system,
                    :lifecycle_state, :is_assignable, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": str(delete_id),
                "group_id": str(source["group_id"]),
                "code": DELETE_CODE,
                "description": DELETE_DESCRIPTION,
                "is_system": source["is_system"],
                "lifecycle_state": source["lifecycle_state"],
                "is_assignable": source["is_assignable"],
            },
        )
    else:
        connection.execute(
            sa.text(
                """
                UPDATE identity_permissions
                SET description=:description, updated_at=CURRENT_TIMESTAMP
                WHERE id=:permission_id
                """
            ),
            {"permission_id": delete_id, "description": DELETE_DESCRIPTION},
        )

    # Existing roles that could remove users through identity.users.update keep
    # that effective access after the permission split.
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT role_id, :delete_id
            FROM identity_role_permissions
            WHERE permission_id=:update_id
            ON CONFLICT DO NOTHING
            """
        ),
        {"update_id": update_id, "delete_id": delete_id},
    )

    # Preserve explicit template exclusions as well: excluding update used to
    # implicitly exclude user removal because both actions shared one permission.
    if sa.inspect(connection).has_table("identity_role_template_exclusions"):
        connection.execute(
            sa.text(
                """
                INSERT INTO identity_role_template_exclusions (role_id, permission_id)
                SELECT role_id, :delete_id
                FROM identity_role_template_exclusions
                WHERE permission_id=:update_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"update_id": update_id, "delete_id": delete_id},
        )

    # CreateUpdateUser must now mean exactly read/create/update. Remove the new
    # delete permission from the template and from uncustomized roles derived
    # from that template. Customized descendants keep their previous access.
    create_update_template_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM identity_roles
            WHERE slug='create_update_user'
              AND role_kind='template'
              AND organization_id IS NULL
              AND deleted_at IS NULL
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if create_update_template_id is not None:
        connection.execute(
            sa.text(
                """
                DELETE FROM identity_role_permissions
                WHERE permission_id=:delete_id
                  AND role_id IN (
                      SELECT id FROM identity_roles
                      WHERE id=:template_id
                         OR (
                             source_template_role_id=:template_id
                             AND permissions_customized=FALSE
                             AND deleted_at IS NULL
                         )
                  )
                """
            ),
            {"delete_id": delete_id, "template_id": create_update_template_id},
        )

    # These system templates/roles must always retain explicit delete access.
    connection.execute(
        sa.text(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            SELECT id, :delete_id
            FROM identity_roles
            WHERE slug IN ('organization_admin', 'full_user')
              AND organization_id IS NULL
              AND deleted_at IS NULL
            ON CONFLICT DO NOTHING
            """
        ),
        {"delete_id": delete_id},
    )


def downgrade() -> None:
    connection = op.get_bind()
    delete_id = _permission_id(connection, DELETE_CODE)

    if delete_id is not None:
        if sa.inspect(connection).has_table("identity_role_template_exclusions"):
            connection.execute(
                sa.text(
                    "DELETE FROM identity_role_template_exclusions WHERE permission_id=:permission_id"
                ),
                {"permission_id": delete_id},
            )
        connection.execute(
            sa.text("DELETE FROM identity_role_permissions WHERE permission_id=:permission_id"),
            {"permission_id": delete_id},
        )
        connection.execute(
            sa.text("DELETE FROM identity_permissions WHERE id=:permission_id"),
            {"permission_id": delete_id},
        )

    connection.execute(
        sa.text(
            """
            UPDATE identity_permissions
            SET description=:description, updated_at=CURRENT_TIMESTAMP
            WHERE code=:code
            """
        ),
        {"code": UPDATE_CODE, "description": LEGACY_UPDATE_DESCRIPTION},
    )
