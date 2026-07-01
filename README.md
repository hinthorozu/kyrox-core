# KYROX Core

**KYROX Core** is a reusable SaaS backend platform. It provides multi-tenant identity, authorization, shared infrastructure services, and API conventions that product applications build on top of—without embedding product-specific domain logic.

## What KYROX Core Is

- A **platform layer** for SaaS backends: tenants, users, roles, permissions, auth, audit, settings, files, and background jobs.
- A **stable foundation** that multiple products can depend on through clear integration contracts.
- An **architecture-first** repository: design and documentation precede implementation.

## What KYROX Core Is Not

- **Not a CRM.** FAIR CRM is the first product using Core; CRM entities and workflows do not belong here.
- **Not product-aware.** Core does not reference, import, or depend on any product repository or domain model.
- **Not a monolith of all KYROX features.** Product-specific business rules, UI concerns, and vertical features stay in product repos.

## Repository Status

| Item | Status |
|------|--------|
| Architecture documentation | Completed (v0.1.0) |
| Backend foundation | Completed (v0.1.0 / Sprint 0.2) |
| Backend architecture standards | Completed (Sprint 0.2.5) |
| Data foundation (SQLAlchemy, Alembic, migrations) | Completed |
| Identity platform (users, organizations, membership) | Completed |
| Authentication (login, refresh, logout, JWT sessions) | Completed |
| Authorization (roles, permissions, guards) | Completed |
| Identity hardening (policy, edge cases, guard tests) | Completed |
| Database migrations | Active (Alembic; identity schema through authorization hardening) |
| Public API endpoints | Health + auth (see below) |
| Platform Services (audit, settings, jobs, notifications) | Not started |
| Product endpoints | Not implemented |

**Test suite:** 62 tests passing (SQLite in CI/local; no PostgreSQL required for tests).

Sprint 0.2 delivered the reusable backend foundation. Sprint 0.2.5 defined layered architecture standards. The Identity Platform (persistence, authentication, authorization, and hardening) is **completed**. The next milestone is **v0.3.0 — Platform Services**.

## Current Status

**Identity Platform — completed**

Delivered:

- Domain entities and repository ports for users, organizations, memberships, roles, and permissions
- Authentication: Argon2id passwords, JWT access tokens, refresh tokens, sessions
- Authorization: role-based permission checks with explicit organization context (`X-Organization-Id` header; no `org_id` in JWT)
- Authorization guard foundation (`require_permission`) for protected routes — **not yet applied to product endpoints**
- Alembic migrations for identity and auth schema
- Architecture and integration tests

**Next milestone: v0.3.0 — Platform Services**

Planned: Audit, Settings, Background Jobs, Notifications.

Run quality checks:

```bash
python scripts/quality_check.py
```

## Public API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Platform health check |
| `POST` | `/api/v1/auth/login` | Email/password login; returns access + refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token; returns new token pair |
| `POST` | `/api/v1/auth/logout` | Revoke session and refresh token |

Authorization guards exist for future protected routes (Bearer JWT + `X-Organization-Id` + permission code). Product-specific API endpoints are not implemented yet.

## Roadmap (Summary)

| Milestone | Focus | Status |
|-----------|--------|--------|
| **v0.1.0** | Foundation — architecture, backend scaffold, data layer, health checks | Completed |
| **v0.2.0** | Identity Platform — users, orgs, membership, auth, authorization, hardening | Completed |
| **v0.3.0** | Platform Services — audit, settings, background jobs, notifications | Planned |
| **v1.0.0** | FAIR CRM integration / production readiness | Later |

See [docs/ROADMAP.md](docs/ROADMAP.md) for sprint details.

## Documentation

Start here:

- **[KYROX Core Architecture](docs/KYROX_CORE_ARCHITECTURE.md)** — purpose, principles, boundaries, and integration rules
- **[Backend Architecture Standards](docs/BACKEND_ARCHITECTURE_STANDARDS.md)** — layered architecture, modules, dependency rules, testing
- **[Identity Platform Design](docs/IDENTITY_PLATFORM_DESIGN.md)** — users, organizations, membership, RBAC, authentication
- **[Roadmap](docs/ROADMAP.md)** — sprint plan through FAIR CRM integration
- **[Decisions](docs/DECISIONS/)** — architecture decision records (ADRs)

## Products Using Core

| Product | Role |
|---------|------|
| **FAIR CRM** | First consumer of KYROX Core (separate repository) |

Products depend on Core. Core never depends on products.

## License

TBD.
