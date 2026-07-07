#!/usr/bin/env python3
"""Idempotent Fair CRM dev identity seed for KYROX Core server deploy.

Creates or updates:
- Organization 00000000-0000-4000-8000-000000000010
- Owner role template with every fair_crm.* permission in the catalog
- dev@example.com / DevPassword123! assigned as owner

Safe to run multiple times; uses ON CONFLICT / existence checks only.
Requires Core Alembic revision >= 20260701_0029.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from argon2 import PasswordHasher

ROOT = Path(__file__).resolve().parents[1]

DEV_EMAIL = os.environ.get("FAIR_CRM_DEV_EMAIL", "dev@example.com")
DEV_PASSWORD = os.environ.get("FAIR_CRM_DEV_PASSWORD", "DevPassword123!")
DEV_USER_ID = os.environ.get("FAIR_CRM_DEV_USER_ID", "00000000-0000-4000-8000-000000000001")
DEV_ORG_ID = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_ID", "00000000-0000-4000-8000-000000000010")
DEV_ORG_NAME = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_NAME", "Fair CRM Dev Org")
DEV_ORG_SLUG = os.environ.get("FAIR_CRM_DEV_ORGANIZATION_SLUG", "fair-crm-dev")
OWNER_ROLE_SLUG = os.environ.get("FAIR_CRM_DEV_ROLE_SLUG", "owner")
OWNER_ROLE_NAME = os.environ.get("FAIR_CRM_DEV_ROLE_NAME", "Owner")

MIN_CORE_MIGRATION_REVISION = os.environ.get("FAIR_CRM_MIN_CORE_MIGRATION", "20260701_0029")

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


def load_fair_crm_permission_ids(cur) -> dict[str, str]:
    cur.execute(
        """
        SELECT code, id
        FROM identity_permissions
        WHERE code LIKE 'fair_crm.%%'
        ORDER BY code
        """
    )
    rows = cur.fetchall()
    if not rows:
        raise SeedError(
            "No fair_crm.* permissions found. "
            "Apply kyrox-core alembic migrations through 20260701_0029 first."
        )
    return {str(code): str(perm_id) for code, perm_id in rows}


def ensure_owner_role_template(cur) -> str:
    cur.execute(
        """
        SELECT id FROM identity_roles
        WHERE scope = 'organization' AND slug = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (OWNER_ROLE_SLUG,),
    )
    row = cur.fetchone()
    if row:
        role_id = str(row[0])
        print(f"Owner role template exists: {role_id}")
        return role_id

    role_id = str(uuid.uuid4())
    now = _now()
    cur.execute(
        """
        INSERT INTO identity_roles (
            id, name, slug, scope, is_system, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'organization', TRUE, %s, %s, NULL)
        """,
        (role_id, OWNER_ROLE_NAME, OWNER_ROLE_SLUG, now, now),
    )
    print(f"Created owner role template: {role_id}")
    return role_id


def grant_fair_crm_permissions(cur, role_id: str, permission_ids: dict[str, str]) -> int:
    granted = 0
    for code in sorted(permission_ids):
        cur.execute(
            """
            INSERT INTO identity_role_permissions (role_id, permission_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (role_id, permission_ids[code]),
        )
        if cur.rowcount:
            granted += 1
    mapped = len(permission_ids)
    print(f"Owner role permissions: {mapped} expected, {granted} newly granted")
    return mapped


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
        print(f"Dev organization exists: {DEV_ORG_ID} (slug={row[1]})")
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


def ensure_dev_user(cur) -> str:
    password_hash = PasswordHasher().hash(DEV_PASSWORD)
    now = _now()

    cur.execute("SELECT id, email FROM identity_users WHERE id = %s LIMIT 1", (DEV_USER_ID,))
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE identity_users
            SET email = %s, password_hash = %s, status = 'active', updated_at = %s, deleted_at = NULL
            WHERE id = %s
            """,
            (DEV_EMAIL, password_hash, now, DEV_USER_ID),
        )
        print(f"Updated dev user: {DEV_EMAIL} ({DEV_USER_ID})")
        return DEV_USER_ID

    cur.execute("SELECT id FROM identity_users WHERE email = %s LIMIT 1", (DEV_EMAIL,))
    by_email = cur.fetchone()
    if by_email:
        user_id = str(by_email[0])
        cur.execute(
            """
            UPDATE identity_users
            SET password_hash = %s, status = 'active', updated_at = %s, deleted_at = NULL
            WHERE id = %s
            """,
            (password_hash, now, user_id),
        )
        print(f"Updated existing dev user by email: {DEV_EMAIL} ({user_id})")
        return user_id

    cur.execute(
        """
        INSERT INTO identity_users (
            id, email, password_hash, status, is_super_admin, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', FALSE, %s, %s, NULL)
        """,
        (DEV_USER_ID, DEV_EMAIL, password_hash, now, now),
    )
    print(f"Created dev user: {DEV_EMAIL} ({DEV_USER_ID})")
    return DEV_USER_ID


def ensure_membership(cur, user_id: str, organization_id: str) -> None:
    cur.execute(
        """
        SELECT id, status FROM identity_memberships
        WHERE user_id = %s AND organization_id = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (user_id, organization_id),
    )
    row = cur.fetchone()
    if row:
        if row[1] != "active":
            cur.execute(
                "UPDATE identity_memberships SET status = 'active', updated_at = %s WHERE id = %s",
                (_now(), str(row[0])),
            )
            print(f"Reactivated membership: {row[0]}")
        return

    now = _now()
    membership_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO identity_memberships (
            id, user_id, organization_id, status,
            invited_at, joined_at, created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', NULL, %s, %s, %s, NULL)
        """,
        (membership_id, user_id, organization_id, now, now, now),
    )
    print(f"Created membership: {membership_id}")


def ensure_organization_role(cur, organization_id: str, role_template_id: str) -> str:
    cur.execute(
        """
        SELECT id FROM identity_organization_roles
        WHERE organization_id = %s AND role_id = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (organization_id, role_template_id),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    now = _now()
    org_role_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO identity_organization_roles (
            id, organization_id, role_id, status, is_default,
            created_at, updated_at, deleted_at
        ) VALUES (%s, %s, %s, 'active', FALSE, %s, %s, NULL)
        """,
        (org_role_id, organization_id, role_template_id, now, now),
    )
    print(f"Created organization role binding: {org_role_id}")
    return org_role_id


def ensure_user_role_assignment(
    cur,
    *,
    user_id: str,
    organization_id: str,
    organization_role_id: str,
) -> None:
    cur.execute(
        """
        SELECT id FROM identity_user_roles
        WHERE user_id = %s
          AND organization_id = %s
          AND organization_role_id = %s
          AND status = 'active'
          AND revoked_at IS NULL
        LIMIT 1
        """,
        (user_id, organization_id, organization_role_id),
    )
    if cur.fetchone():
        return

    now = _now()
    user_role_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO identity_user_roles (
            id, user_id, organization_id, organization_role_id,
            status, assigned_at, revoked_at, assigned_by, created_at
        ) VALUES (%s, %s, %s, %s, 'active', %s, NULL, %s, %s)
        """,
        (user_role_id, user_id, organization_id, organization_role_id, now, user_id, now),
    )
    print(f"Assigned dev user to owner role: {user_role_id}")


def verify_no_duplicate_role_permissions(cur, role_id: str) -> None:
    cur.execute(
        """
        SELECT permission_id, COUNT(*) AS cnt
        FROM identity_role_permissions
        WHERE role_id = %s
        GROUP BY permission_id
        HAVING COUNT(*) > 1
        """,
        (role_id,),
    )
    dupes = cur.fetchall()
    if dupes:
        raise SeedError(f"Duplicate role-permission mappings detected for role {role_id}")


def main() -> int:
    print(f"Seeding Fair CRM dev identity against {CORE_DB_URL.split('@')[-1]}")
    conn = _connect(CORE_DB_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            assert_core_migration_ready(cur)
            permission_ids = load_fair_crm_permission_ids(cur)
            owner_role_id = ensure_owner_role_template(cur)
            mapped = grant_fair_crm_permissions(cur, owner_role_id, permission_ids)
            verify_no_duplicate_role_permissions(cur, owner_role_id)

            org_id = ensure_dev_organization(cur)
            user_id = ensure_dev_user(cur)
            ensure_membership(cur, user_id, org_id)
            org_role_id = ensure_organization_role(cur, org_id, owner_role_id)
            ensure_user_role_assignment(
                cur,
                user_id=user_id,
                organization_id=org_id,
                organization_role_id=org_role_id,
            )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM identity_role_permissions rp
                JOIN identity_permissions p ON p.id = rp.permission_id
                WHERE rp.role_id = %s AND p.code LIKE 'fair_crm.%%'
                """,
                (owner_role_id,),
            )
            count_row = cur.fetchone()
            if count_row is None:
                raise SeedError("Could not verify owner role fair_crm permission count")
            final_mapped = int(count_row[0])
            if final_mapped < mapped:
                raise SeedError(
                    f"Owner role mapping incomplete: {final_mapped}/{mapped} fair_crm permissions"
                )

        conn.commit()
        print(
            "Seed complete:",
            f"user={DEV_EMAIL}",
            f"org={DEV_ORG_ID}",
            f"permissions={final_mapped}",
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
