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
| Architecture documentation | In progress (Sprint 0.1) |
| Backend foundation | Completed (Sprint 0.2) |
| Backend architecture standards | Completed (Sprint 0.2.5) |
| Database migrations | Not started |
| Public API endpoints | Health check only (`GET /api/v1/health`) |

Sprint 0.2 delivered the reusable backend foundation. Sprint 0.2.5 defined layered architecture standards before Identity Platform implementation.

## Current Sprint

**Sprint 0.2.5 — Backend Architecture Standards** (completed)

Delivered:

- [Backend Architecture Standards](docs/BACKEND_ARCHITECTURE_STANDARDS.md) — layers, dependency rules, patterns, testing
- [ADR 0002: Backend Layered Architecture](docs/DECISIONS/0002-backend-layered-architecture.md)
- Module layout convention for `modules/<name>/{domain,application,infrastructure,api}`

Run quality checks:

```bash
python scripts/quality_check.py
```

Next up: **Sprint 0.3 — Identity Platform** (auth, users, tenants, RBAC)

## Roadmap (Summary)

| Sprint | Focus |
|--------|--------|
| **0.1** | Architecture — documentation and boundaries |
| **0.2** | Backend foundation — project structure, tooling, health checks |
| **0.2.5** | Backend architecture standards — layer boundaries, dependency rules, testing |
| **0.3** | Identity Platform — auth, users, tenants, RBAC |
| **0.4** | Audit, settings, files, background jobs |
| **1.0** | FAIR CRM integration preparation |

See [docs/ROADMAP.md](docs/ROADMAP.md) for sprint details.

## Documentation

Start here:

- **[KYROX Core Architecture](docs/KYROX_CORE_ARCHITECTURE.md)** — purpose, principles, boundaries, and integration rules
- **[Backend Architecture Standards](docs/BACKEND_ARCHITECTURE_STANDARDS.md)** — layered architecture, modules, dependency rules, testing
- **[Roadmap](docs/ROADMAP.md)** — sprint plan through FAIR CRM integration
- **[Decisions](docs/DECISIONS/)** — architecture decision records (ADRs)

## Products Using Core

| Product | Role |
|---------|------|
| **FAIR CRM** | First consumer of KYROX Core (separate repository) |

Products depend on Core. Core never depends on products.

## License

TBD.
