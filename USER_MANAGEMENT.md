# User Management

Kyrox Core provides reusable identity user-management capabilities for applications such as Fair CRM.

## User creation

Administrators can add a user to an organization in two ways:

1. Invitation by email.
2. Direct creation with a temporary password.

Users created with a temporary password are stored with `must_change_password=true`. Protected API access is blocked until the user successfully changes the password through the authenticated password-change flow.

## Organization membership

User creation is organization-scoped. Creating or inviting a user associates the resulting account with the selected organization through membership.

## Authorization

Reusable identity permissions cover user and role management. Super-admin authorization is handled centrally and is not coupled to Fair CRM-specific application logic.

## Admin organization management

Global super-admin organization management is exposed under `/api/v1/admin/organizations` and supports list, create, read, update and soft-delete operations.

## Database migration

`20260814_0037_user_management.py` seeds the user/role management permission data against the existing `identity_permission_groups` and `identity_permissions` schema. Downgrade removes dependent `identity_role_permissions` rows before removing permissions so foreign-key constraints remain valid.

## Validation

The feature branch was validated with the repository migration/test workflow before merge to main.
