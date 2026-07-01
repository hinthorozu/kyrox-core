# KYROX Core — Product Integration Guide

**Version:** v0.4.0+ (product integration APIs)  
**Audience:** Product teams (e.g. FAIR CRM) integrating with KYROX Core as an **independent platform service**

---

## 1. Overview

KYROX Core is a **standalone backend platform service**. Product applications are **separate services** that integrate through **Core public HTTP APIs** under `/api/v1`.

Products must **not**:

- Import kyrox-core Python packages
- Share a database or SQLAlchemy session with Core
- Mount Core routers inside the product application

Products **must**:

- Authenticate users through Core
- Pass organization context on org-scoped calls
- Use Core APIs for platform capabilities (audit, settings, jobs, notifications)
- Store product domain data in the product's own database

---

## 2. Runtime topology

```text
Client  ──►  KYROX Core (:8000)     auth, orgs, RBAC, platform services
Client  ──►  Product app (:8001)    product domain APIs

Product app ──HTTP──► KYROX Core    permission check, audit write, settings, jobs, notifications
```

Each service has its own database. Product tables reference Core `organization_id` as an opaque UUID — no cross-database foreign keys.

---

## 3. Authentication

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{"email": "user@example.com", "password": "..."}
```

Response includes `access_token` and `refresh_token`.

### Refresh and logout

| Method | Path |
|--------|------|
| `POST` | `/api/v1/auth/refresh` |
| `POST` | `/api/v1/auth/logout` |

### JWT access token

Core issues signed JWT access tokens. Claims include:

| Claim | Meaning |
|-------|---------|
| `sub` | User id (UUID) |
| `email` | User email |
| `sid` | Session id (UUID) |
| `exp`, `iat`, `jti` | Expiry and token metadata |

**Organization is not embedded in the JWT.** Tenant context is supplied per request.

### Product-side validation

Product services validate access tokens locally using the same `JWT_SECRET_KEY` and `JWT_ALGORITHM` configured on Core (environment alignment — not a code import).

Reject expired or invalid tokens with `401 Unauthorized`.

---

## 4. Organization context

Org-scoped Core and product routes require:

```http
Authorization: Bearer <access_token>
X-Organization-Id: <organization_uuid>
```

Rules:

- Path `{organization_id}` must match `X-Organization-Id` or Core returns `400 Organization scope mismatch`.
- The user must have an **active organization membership** (or be a platform super-admin) for org-scoped integration endpoints.

---

## 5. Authorization (RBAC)

### Permission code format

Dot-separated, lowercase, minimum three segments:

```text
{module}.{resource}.{verb}
```

Examples:

| Code | Owner |
|------|-------|
| `audit.logs.read` | Core platform |
| `settings.platform.read` | Core platform |
| `fair_crm.customers.read` | Product (registered in Core RBAC) |

### Permission modules

Core platform modules: `audit`, `core`, `identity`, `jobs`, `notifications`, `settings`.

Product modules use the same naming rules (e.g. `fair_crm`). Product permission codes are stored in Core's RBAC tables and assigned to roles — products do not reimplement RBAC.

### FAIR CRM customer permissions (seeded)

Migration `20260701_0025` registers:

| Code | Description |
|------|-------------|
| `fair_crm.customers.create` | Create CRM customers |
| `fair_crm.customers.read` | Read CRM customers |
| `fair_crm.customers.update` | Update CRM customers |
| `fair_crm.customers.archive` | Archive CRM customers |

Assign these codes to organization roles in Core. Products check them via the authorization check API above.

### Check permission (product integration API)

Products call Core to verify whether the **current user** has a permission in the **current organization**:

```http
POST /api/v1/organizations/{organization_id}/authorization/check
Authorization: Bearer <access_token>
X-Organization-Id: <organization_uuid>
Content-Type: application/json

{"permission_code": "fair_crm.customers.read"}
```

Response:

```json
{"allowed": true, "permission_code": "fair_crm.customers.read"}
```

Notes:

- Requires authentication and active organization membership.
- Does **not** require the permission being checked — use this before enforcing product route access.
- Returns `allowed: false` when the user lacks the permission (HTTP 200, not 403).

Protected Core routes use `require_permission` internally and return `403` when denied.

---

## 6. Organization and membership

| Operation | API |
|-----------|-----|
| Create organization | `POST /api/v1/organizations` |
| Get organization | `GET /api/v1/organizations/{id}` |
| List memberships | `GET /api/v1/organizations/{id}/memberships` |
| Invite member | `POST /api/v1/organizations/{id}/memberships/invite` |
| Accept invite | `POST /api/v1/memberships/invites/accept` |

Products consume these APIs directly or via client apps. Products do not reimplement org/membership lifecycle.

---

## 7. Audit

### Write (product integration API)

Products append org-scoped audit events:

```http
POST /api/v1/organizations/{organization_id}/audit-events
Authorization: Bearer <access_token>
X-Organization-Id: <organization_uuid>
Content-Type: application/json

{
  "action": "fair_crm.customer.created",
  "resource_type": "customer",
  "resource_id": "550e8400-e29b-41d4-a716-446655440000",
  "new_values": {"display_name": "Example Co"},
  "metadata": {"source": "api"}
}
```

Response: `201 Created` with the recorded audit event.

Rules:

- **Append-only** — no update or delete APIs.
- Requires authentication and active organization membership.
- `action` must follow `module.resource.action` naming (e.g. `fair_crm.customer.created`).
- `user_id` and `session_id` are taken from the JWT — callers cannot impersonate another user.
- Do not store passwords, tokens, or secrets in `old_values`, `new_values`, or `metadata`.

### Query

```http
GET /api/v1/organizations/{organization_id}/audit-logs
```

Requires permission `audit.logs.read`. Supports cursor pagination and filters (`action`, `action_prefix`, `resource_type`, etc.).

**Product integration note:** Products such as FAIR CRM may treat audit **writes** as best-effort in early sprints — CRM operations should not fail solely because the audit API is unavailable. Products should log audit write failures clearly at warning level.

---

## 8. Settings

Org-scoped key/value settings (opaque JSON):

| Method | Path |
|--------|------|
| `GET` | `/organizations/{id}/settings` |
| `GET` | `/organizations/{id}/settings/{key}` |
| `PUT` | `/organizations/{id}/settings/{key}` |
| `DELETE` | `/organizations/{id}/settings/{key}` |

Permissions: `settings.platform.read`, `settings.platform.update`.

Product keys use a product namespace:

```text
fair_crm.customers.default_status
fair_crm.import.preview_required
```

Core stores values without interpreting product schemas.

System settings (`/api/v1/system/settings/...`) require platform super-admin.

---

## 9. Background jobs

| Method | Path | Permission |
|--------|------|------------|
| `POST` | `/organizations/{id}/jobs` | `jobs.platform.enqueue` |
| `GET` | `/jobs/{id}` | `jobs.platform.read` |

Enqueue example:

```json
{
  "job_type": "fair_crm.import.process_batch",
  "payload": {"batch_id": "..."}
}
```

Product job **handlers** execute in the product service (or product worker). Core stores job metadata and dispatch status.

---

## 10. Notifications

| Method | Path | Permission |
|--------|------|------------|
| `POST` | `/organizations/{id}/notifications/send` | `notifications.platform.send` |
| `GET` | `/notifications/{id}` | `notifications.platform.read` |

Products pass rendered subject/body or template metadata. Core dispatches asynchronously via the jobs platform.

---

## 11. Error handling

Core returns standard HTTP status codes:

| Code | Meaning |
|------|---------|
| `400` | Validation error or organization scope mismatch |
| `401` | Missing or invalid token |
| `403` | Permission denied (protected Core routes) or inactive membership |
| `404` | Resource not found |
| `422` | Request schema validation failed |

Error body shape: `{"detail": "..."}`.

---

## 12. Product integration checklist

1. Configure `KYROX_CORE_BASE_URL` and matching JWT validation settings.
2. Direct clients to Core for login; reuse access token on product API.
3. Send `X-Organization-Id` on every org-scoped product request.
4. Call `POST .../authorization/check` before enforcing product permissions.
5. Register product permission codes in Core RBAC (migrations or admin process).
6. Emit audit events via `POST .../audit-events` after successful product mutations.
7. Use settings/jobs/notifications APIs instead of reimplementing platform logic.
8. Keep product domain data in the product database only.

---

## 13. Health

```http
GET /api/v1/health
```

Use for load balancer and local development smoke checks.

---

## 14. Versioning

- Current API version prefix: `/api/v1`
- Pin product integrations to tagged Core releases (e.g. `v0.4.0`).
- Breaking API changes require a new version prefix and migration notes.

---

## 15. Related documents

- [KYROX Core Architecture](KYROX_CORE_ARCHITECTURE.md)
- [Backend Architecture Standards](BACKEND_ARCHITECTURE_STANDARDS.md)
- [Platform Services Design](PLATFORM_SERVICES_DESIGN.md)
- [Identity Platform Design](IDENTITY_PLATFORM_DESIGN.md)
- kyrox-platform [ADR-0004 Audit service strategy](../../kyrox-platform/decisions/0004-audit-service-strategy.md)
