#!/usr/bin/env python3
"""Idempotent KYROX Core development identity seed.

Canonical development identity model:
- Keep/create the Fair CRM development organization.
- Keep/create only dev@example.com as the bootstrap platform user.
- dev@example.com is always DB-backed Super Admin (is_super_admin = TRUE).
- Super Admin is platform-wide and therefore receives no organization
  membership, organization role, or RBAC permission mapping from this seed.
- The deprecated Owner role is removed if an older seed recreated it.

Safe to run multiple times.
Requires Core Alembic revision >= 20260814_0044.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import psycopg2
from argon2 import PasswordHasher

DEV_EMAIL = os.environ.get("FAIR_CRM_DEV_EMAIL", "dev@example.com")
DEV_PASSWORD = os.environ.get("FAIR_CRM_DEV_PASSWORD", "DevPassword123!")
DEV_USER_ID = os.environ.get("FAIR_CRM_DEV_USER_ID", "00000000-0000-4000-8000-000000000001")
DEV_ORG_ID = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_ID", "00000000-0000-4000-8000-000000000010")
DEV_ORG_NAME = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_NAME", "Fair CRM Dev Org")
DEV_ORG_SLUG = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_SLUG", "fair-crm-dev")

MIN_CORE_MIGRATION_REVISION = os.environ.get("FAIR_CRM_MIN_CORE_MIGRATION", "20260814_0044")

CORE_DB_URL = os.environ.get(
    "KYROX_CORE_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/kyrox_core",
    ),
)


class SeedError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _connect(db_url: str):
    return psycopg2.connect(db_url)


def assert_core_migration_ready(cur) -> str:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'alembic_version'
        )
        """
    )
    if not cur.fetchone()[0]:
        raise SeedError("Core database has no alembic_version table. Run alembic upgrade head first.")

    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
    row = cur.fetchone()
    if row is None:
        raise SeedError("Core alembic_version is empty. Run alembic upgrade head first.")

    current = str(row[0])
    if current < MIN_CORE_MIGRATION_REVISION:
        raise SeedError(
            f"Core migration {current} is below required {MIN_CORE_MIGRATION_REVISION}. "
            "Run kyrox-core alembic upgrade head."
        )
    print(f"Core migration OK: {current} (required >= {MIN_CORE_MIGRATION_REVISION})")
    return current


def ensure_dev_organization(cur) -> str:
    cur.execute(
        """
        SELECT id, slug FROM identity_organizations
        WHERE id = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (DEV_ORG_ID,),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE identity_organizations
            SET name = %s, slug = %s, status = 'active', updated_at = %s, deleted_at = NULL
            WHERE id = %s
            """,
            (DEV_ORG_NAME, DEV_ORG_SLUG, _now(), DEV_ORG_ID),
        )
        print(f"Dev organization exists: {DEV_ORG_ID}")
        return str(row[0])

    cur.execute(
        """
        SELECT id FROM identity_organizations
        WHERE slug = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (DEV_ORG_SLUG,),
    )
    slug_row = cur.fetchone()
    if slug_row and str(slug_row[0]) != DEV_ORG_ID:
        raise SeedError(
            f"Organization slug '{DEV_ORG_SLUG}' already used by {slug_row[0]}. "
            "Choose a different FAIR_CRM_DEV_ORGANIZATION_SLUG."
        )

    now = _now()
    cur.execute(
        """
        INSERT INTO identity_organizations (
            id, name, slug, status, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', %s, %s, NULL)
        """,
        (DEV_ORG_ID, DEV_ORG_NAME, DEV_ORG_SLUG, now, now),
    )
    print(f"Created dev organization: {DEV_ORG_NAME} ({DEV_ORG_ID})")
    return DEV_ORG_ID


def ensure_dev_super_admin(cur) -> str:
    password_hash = PasswordHasher().hash(DEV_PASSWORD)
    now = _now()

    cur.execute("SELECT id FROM identity_users WHERE id = %s LIMIT 1", (DEV_USER_ID,))
    row = cur.fetchone()
    if row:
        user_id = str(row[0])
        cur.execute(
            """
            UPDATE identity_users
            SET email = %s,
                password_hash = %s,
                status = 'active',
                is_super_admin = TRUE,
                updated_at = %s,
                deleted_at = NULL
            WHERE id = %s
            """,
            (DEV_EMAIL, password_hash, now, user_id),
        )
        print(f"Updated dev Super Admin: {DEV_EMAIL} ({user_id})")
        return user_id

    cur.execute("SELECT id FROM identity_users WHERE lower(email) = lower(%s) LIMIT 1", (DEV_EMAIL,))
    by_email = cur.fetchone()
    if by_email:
        user_id = str(by_email[0])
        cur.execute(
            """
            UPDATE identity_users
            SET password_hash = %s,
                status = 'active',
                is_super_admin = TRUE,
                updated_at = %s,
                deleted_at = NULL
            WHERE id = %s
            """,
            (password_hash, now, user_id),
        )
        print(f"Promoted existing dev user to Super Admin: {DEV_EMAIL} ({user_id})")
        return user_id

    cur.execute(
        """
        INSERT INTO identity_users (
            id, email, password_hash, status, is_super_admin,
            created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', TRUE, %s, %s, NULL)
        """,
        (DEV_USER_ID, DEV_EMAIL, password_hash, now, now),
    )
    print(f"Created dev Super Admin: {DEV_EMAIL} ({DEV_USER_ID})")
    return DEV_USER_ID


def remove_super_admin_org_assignments(cur, user_id: str) -> None:
    """Super Admin is platform-level; old org-scoped assignments are legacy state."""
    cur.execute("DELETE FROM identity_user_roles WHERE user_id = %s", (user_id,))
    removed_roles = cur.rowcount
    cur.execute("DELETE FROM identity_memberships WHERE user_id = %s", (user_id,))
    removed_memberships = cur.rowcount
    if removed_roles or removed_memberships:
        print(
            "Removed legacy Super Admin organization state:",
            f"user_roles={removed_roles}",
            f"memberships={removed_memberships}",
        )


def remove_deprecated_owner_role(cur) -> None:
    """Never allow the historical Owner organization role to reappear."""
    cur.execute(
        """
        DELETE FROM identity_roles
        WHERE scope = 'organization' AND slug = 'owner'
        """
    )
    if cur.rowcount:
        print(f"Removed deprecated Owner role templates: {cur.rowcount}")


def verify_super_admin(cur, user_id: str) -> None:
    cur.execute(
        """
        SELECT status, is_super_admin, deleted_at
        FROM identity_users
        WHERE id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    if row is None or row[0] != "active" or row[1] is not True or row[2] is not None:
        raise SeedError("dev@example.com was not persisted as an active Super Admin")

    cur.execute("SELECT COUNT(*) FROM identity_memberships WHERE user_id = %s", (user_id,))
    if int(cur.fetchone()[0]) != 0:
        raise SeedError("Super Admin must not have organization memberships after seed")

    cur.execute("SELECT COUNT(*) FROM identity_user_roles WHERE user_id = %s", (user_id,))
    if int(cur.fetchone()[0]) != 0:
        raise SeedError("Super Admin must not have organization role assignments after seed")


def main() -> int:
    print(f"Seeding KYROX Core dev Super Admin against {CORE_DB_URL.split('@')[-1]}")
    conn = _connect(CORE_DB_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            assert_core_migration_ready(cur)
            ensure_dev_organization(cur)
            user_id = ensure_dev_super_admin(cur)
            remove_super_admin_org_assignments(cur, user_id)
            remove_deprecated_owner_role(cur)
            verify_super_admin(cur, user_id)

        conn.commit()
        print(
            "Seed complete:",
            f"user={DEV_EMAIL}",
            "is_super_admin=true",
            "organization_memberships=0",
            "organization_roles=0",
        )
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
