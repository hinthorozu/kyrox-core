# ADR 0002: Backend Layered Architecture

| Field | Value |
|-------|--------|
| **Status** | Accepted |
| **Date** | 2026-07-01 |
| **Sprint** | 0.2.5 — Backend Architecture Standards |

## Context

Sprint 0.2 delivered a minimal FastAPI foundation: configuration, logging, exception handling, a health endpoint, and a database session placeholder. Sprint 0.3 will implement the **Identity Platform** (auth, users, tenants, RBAC)—the first substantial domain module.

Without explicit layer boundaries, platform backends commonly collapse into:

- Fat controllers containing business logic and SQL
- Domain rules coupled to SQLAlchemy models and HTTP schemas
- Infrastructure concerns leaking into every layer
- Product-specific shortcuts embedded in shared code

KYROX Core must serve **multiple products** (starting with FAIR CRM). That requires a structure that stays testable, reusable, and free of product domain leakage as complexity grows.

## Decision

**KYROX Core backend code will follow a layered architecture with strict dependency rules.**

### Layers

1. **Domain** — business rules, entities, and port interfaces. No I/O or framework imports.
2. **Application** — use cases / application services orchestrating domain logic through ports.
3. **Infrastructure** — SQLAlchemy repositories, external adapters, ORM models, mappers.
4. **API** — thin FastAPI routers and Pydantic request/response schemas.

### Module layout

Platform capabilities are organized under `backend/app/modules/<name>/` with `domain/`, `application/`, `infrastructure/`, and `api/` subpackages. Cross-cutting wiring remains in `backend/app/core/`. Global HTTP aggregation remains in `backend/app/api/v1/`.

### Supporting patterns

- **Repository pattern:** port interfaces in domain/application; SQLAlchemy implementations in infrastructure.
- **Application service layer:** one use case per workflow; API handlers delegate without business logic.
- **Dependency injection:** constructor injection wired via FastAPI `Depends()` at the composition root.
- **Schema separation:** API schemas, application DTOs, and domain entities are distinct types with explicit mapping.

### Import boundaries (summary)

- Domain must not import infrastructure or API.
- Application may import domain only (plus application DTOs).
- Infrastructure implements ports and may import domain.
- API calls application services; it must not access repositories or ORM directly.

Full rules are documented in [Backend Architecture Standards](../BACKEND_ARCHITECTURE_STANDARDS.md).

## Why Layer Boundaries Matter

| Concern | Without layers | With layers |
|---------|----------------|-------------|
| Testing business rules | Requires HTTP and database | Domain and use cases tested in isolation |
| Changing database technology | Ripples through controllers | Contained in infrastructure |
| Adding API versions | Duplicates business logic | Reuses application services |
| Onboarding new modules | Inconsistent patterns | Repeatable module template |
| Security (tenant isolation) | Easy to bypass in ad-hoc SQL | Enforced in use cases and repositories |

Clear boundaries make code review objective: violations are visible as import errors or architectural test failures.

## Why Core Must Avoid Product-Specific Dependencies

KYROX Core is a **platform**, not a product. [ADR 0001](0001-core-product-separation.md) established that FAIR CRM and future products depend on Core—not the reverse.

Layered architecture reinforces product independence:

- Product domain (CRM deals, contacts, pipelines) never enters Core modules.
- Core use cases speak in platform terms: tenant, user, role, permission, audit event.
- Products integrate through public APIs; they do not import Core `infrastructure/` or `domain/` internals.
- A single architectural style across modules prevents "special case" CRM shortcuts in shared code.

If product logic appears in Core, every future product inherits CRM assumptions—defeating the purpose of a shared platform.

## Consequences

### Positive

- Consistent module template for identity, audit, settings, files, and jobs.
- Business rules testable without PostgreSQL or HTTP.
- Reviewers can enforce boundaries with a documented import matrix.
- FAIR CRM integration (Sprint 1.0) consumes stable application-level contracts.

### Negative / Trade-offs

- More files and mapping boilerplate than a single-layer CRUD app.
- Team must learn and respect layer rules; occasional pragmatism requires ADR updates, not silent shortcuts.
- Initial Sprint 0.3 setup cost to scaffold `modules/identity/` correctly.

## Compliance

All backend pull requests from Sprint 0.3 onward must comply with [Backend Architecture Standards](../BACKEND_ARCHITECTURE_STANDARDS.md).

Reject or refactor code that:

- Places SQLAlchemy queries in API or application layers
- Skips repository ports for direct ORM access from use cases
- Embeds product-specific entities or branching in Core
- Exposes ORM models as API response types

## Related Documents

- [Backend Architecture Standards](../BACKEND_ARCHITECTURE_STANDARDS.md)
- [ADR 0001: Core / Product Separation](0001-core-product-separation.md)
- [KYROX Core Architecture](../KYROX_CORE_ARCHITECTURE.md)
- [Roadmap](../ROADMAP.md)
