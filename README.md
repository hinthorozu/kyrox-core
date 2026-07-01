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
| Identity platform — authentication & authorization | Completed (v0.2.0) |
| Identity platform — organization & membership | Completed (**v0.3.0**) |
| Database migrations | Active (Alembic head: `20260701_0016`) |
| Public API endpoints | Health, auth, organizations, memberships |
| Platform Services (audit API, settings, jobs, notifications) | Planned (Sprint 0.4.0) |
| Product endpoints | Not implemented |

**Test suite:** 228 tests passing, 1 skipped (SQLite in CI/local; no PostgreSQL required for tests).

**Latest release:** [v0.3.0](CHANGELOG.md#030--2026-07-01) — Organization & Membership Platform (Sprint 0.3.5).

## Current Status

**Identity Platform — completed (v0.3.0)**

Delivered across Sprint 0.3.2–0.3.5:

- Authentication: Argon2id passwords, JWT access tokens, refresh tokens, sessions
- Authorization: RBAC with `require_permission`, explicit `X-Organization-Id` header
- Organization & membership: canonical domain, invite/accept flow, org CRUD API
- Alembic migrations through membership schema cleanup (`20260701_0016`)
- Architecture, migration, and API tests

**Next milestone: v0.4.0 — Platform Services**

Planned: Audit query API, Settings, Background Jobs, Notifications. See [Platform Services Design](docs/PLATFORM_SERVICES_DESIGN.md).

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
| `POST` | `/api/v1/organizations` | Create organization (JWT; owner from token) |
| `GET` | `/api/v1/organizations/{id}` | Get organization (`identity.organizations.read`) |
| `PATCH` | `/api/v1/organizations/{id}` | Update organization (`identity.organizations.update`) |
| `POST` | `/api/v1/organizations/{id}/suspend` | Suspend organization (`identity.organizations.update`) |
| `GET` | `/api/v1/organizations/{id}/memberships` | List memberships (`identity.memberships.read`) |
| `POST` | `/api/v1/organizations/{id}/memberships/invite` | Invite member (`identity.memberships.invite`) |
| `POST` | `/api/v1/memberships/invites/accept` | Accept invite (JWT only) |
| `POST` | `/api/v1/memberships/{id}/suspend` | Suspend membership (`identity.memberships.update`) |
| `DELETE` | `/api/v1/memberships/{id}` | Remove membership (`identity.memberships.remove`) |

Protected org-scoped routes require `Authorization: Bearer <token>` and `X-Organization-Id: <uuid>`.

## Roadmap (Summary)

| Milestone | Focus | Status |
|-----------|--------|--------|
| **v0.1.0** | Foundation — architecture, backend scaffold, data layer, health checks | Completed |
| **v0.2.0** | Identity — auth, authorization, legacy persistence, hardening | Completed |
| **v0.3.0** | Identity — organization & membership (full stack) | Completed |
| **v0.4.0** | Platform Services — audit, settings, jobs, notifications | Planned |
| **v1.0.0** | FAIR CRM integration / production readiness | Later |

See [docs/ROADMAP.md](docs/ROADMAP.md) for sprint details.

## Documentation

Start here:

- **[Backend Architecture Standards](docs/BACKEND_ARCHITECTURE_STANDARDS.md)** — layered architecture, modules, dependency rules, testing
- **[Identity Platform Design](docs/IDENTITY_PLATFORM_DESIGN.md)** — users, organizations, membership, RBAC, authentication
- **[Platform Services Design](docs/PLATFORM_SERVICES_DESIGN.md)** — Sprint 0.4.0 backlog and technical proposal
- **[Roadmap](docs/ROADMAP.md)** — sprint plan through FAIR CRM integration
- **[Changelog](CHANGELOG.md)** — release history
- **[Decisions](docs/DECISIONS/)** — architecture decision records (ADRs)

## Products Using Core

| Product | Role |
|---------|------|
| **FAIR CRM** | First consumer of KYROX Core (separate repository) |

Products depend on Core. Core never depends on products.

## License

TBD.
