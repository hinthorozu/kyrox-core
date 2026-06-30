# Backend Architecture Standards

This document defines how KYROX Core backend code is structured, layered, and tested. It applies to all Core modules (identity, audit, settings, files, jobs, and future platform capabilities).

**Scope:** Architecture and conventions only. Sprint 0.2.5 does not implement business logic.

**Related documents:**

- [KYROX Core Architecture](KYROX_CORE_ARCHITECTURE.md)
- [ADR 0001: Core / Product Separation](DECISIONS/0001-core-product-separation.md)
- [ADR 0002: Backend Layered Architecture](DECISIONS/0002-backend-layered-architecture.md)
- [Roadmap](ROADMAP.md)

---

## 1. Layered Architecture

KYROX Core uses a **layered (ports and adapters) architecture** inside each platform module.

| Layer | Purpose |
|-------|---------|
| **Domain** | Core business rules, entities, value objects, and port interfaces. No framework or I/O. |
| **Application** | Use cases / application services orchestrating domain logic via ports. |
| **Infrastructure** | Concrete implementations: SQLAlchemy repositories, external APIs, messaging, file storage. |
| **API** | HTTP transport: routes, request/response mapping, auth middleware hooks. Thin controllers only. |

Dependency direction is **inward**:

```text
API -> Application -> Domain
Infrastructure -> Domain (implements ports)
Infrastructure -> Application (implements ports, when needed)
```

The domain layer must not depend on outer layers.

---

## 2. Module Structure

### 2.1 Top-level layout

```text
backend/app/
  core/                    # Cross-cutting platform wiring (not business domain)
    config.py
    logging.py
    exceptions.py

  shared/                  # Reusable building blocks across modules (optional sub-layers)
    domain/
    application/
    infrastructure/
    api/

  modules/                 # Platform capability modules
    identity/              # Sprint 0.3+ (example; not implemented in 0.2.5)
      domain/
      application/
      infrastructure/
      api/

  api/                     # Global HTTP surface
    v1/
      router.py            # Aggregates module routers + platform routes
      health.py            # Platform health (unchanged)
```

### 2.2 Module rules

- Each platform capability lives under `modules/<name>/` with the four layers.
- `core/` holds app-wide configuration, logging, and exception primitives only.
- `shared/` holds cross-module primitives (base types, common ports) when duplication would otherwise occur.
- Global routing lives under `app/api/v1/` and **includes** module routers; modules do not replace the global API root.
- Products (FAIR CRM, etc.) **never** live under `backend/app/`. Products are separate repositories.

### 2.3 Naming conventions

| Layer | Typical contents |
|-------|------------------|
| `domain/` | Entities, value objects, domain services, repository **interfaces** (ports) |
| `application/` | Use case classes, application services, DTOs for use-case I/O |
| `infrastructure/` | SQLAlchemy models, repository implementations, adapters |
| `api/` | FastAPI routers, request/response schemas, dependency wiring |

---

## 3. Layer Responsibilities

### 3.1 Domain

- Express platform invariants and rules (e.g. "a tenant slug must be unique", "permissions are tenant-scoped").
- Define **port interfaces** (e.g. `UserRepository`, `TenantRepository`) as abstract contracts.
- Remain free of FastAPI, SQLAlchemy, Pydantic request models, and HTTP concepts.
- No database session management.

### 3.2 Application

- Implement **use cases** (one class or function per workflow: `CreateUser`, `AssignRole`, `ResolveTenant`).
- Coordinate domain entities and ports; enforce transaction boundaries at this layer when needed.
- Accept plain inputs / application DTOs; return application results or domain objects.
- Must not construct HTTP responses or read raw request objects.

### 3.3 Infrastructure

- Implement domain/application **ports** with concrete technology (SQLAlchemy, Redis, S3, etc.).
- Own ORM models, mappers, and persistence queries.
- May import domain types and port interfaces.
- Must not expose ORM models to the API layer directly.

### 3.4 API

- Map HTTP requests to application service calls.
- Validate and serialize via Pydantic **API schemas** (separate from domain entities).
- Translate application/domain errors to HTTP status codes using shared exception types.
- Stay **thin**: no business rules, no direct database access, no SQLAlchemy queries.

---

## 4. Dependency Rules

### 4.1 Allowed imports

| From | May import |
|------|------------|
| `domain` | Standard library; other `domain` types in the same or `shared/domain` module |
| `application` | `domain`; `shared/application`; application DTOs in same module |
| `infrastructure` | `domain`; port interfaces; SQLAlchemy and infra libraries; `core.config` for wiring |
| `api` | `application` services; API schemas; `core.exceptions`; FastAPI |
| `core` | Standard library; config/logging libraries only (no module domain) |
| `app/api/v1` | Module `api` routers; `core`; health and platform routes |

### 4.2 Forbidden imports

| Layer | Must NOT import |
|-------|-----------------|
| `domain` | `infrastructure`, `api`, FastAPI, SQLAlchemy, Pydantic API schemas |
| `application` | `infrastructure`, `api`, FastAPI, SQLAlchemy ORM models |
| `infrastructure` | `api`, FastAPI routers |
| `api` | SQLAlchemy ORM models, repository implementations directly |
| Any Core module | Product packages, FAIR CRM types, product-specific enums or workflows |

**Rule of thumb:** if a change in HTTP routing or database technology should not force a domain rewrite, the dependency is wrong.

---

## 5. Repository Pattern

**Decision:** Use the repository pattern with **interfaces (ports) in domain or application**, and **SQLAlchemy implementations in infrastructure**.

### 5.1 Port definition (domain or application)

```python
# modules/identity/domain/ports/user_repository.py (illustrative)
class UserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def save(self, user: User) -> None: ...
```

### 5.2 Implementation (infrastructure)

```python
# modules/identity/infrastructure/repositories/sqlalchemy_user_repository.py (illustrative)
class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None: ...
```

### 5.3 Rules

- Application services depend on the **port**, not the concrete class.
- Repositories return **domain entities** or domain-friendly types, not ORM instances.
- One repository per aggregate root unless a documented exception exists.
- Complex queries stay inside infrastructure; domain does not compose SQL.

---

## 6. Service Layer (Application / Use Cases)

**Decision:** Use **application services (use cases)** for business workflows. API endpoints must stay thin.

### 6.1 Structure

- One use case per user-facing operation or cohesive workflow.
- Use cases are invoked by API handlers and by background jobs (future), not by other use cases deeply nested without clear boundaries.
- Shared steps extract to domain services or small application helpers—not copy-pasted across use cases.

### 6.2 Example flow

```text
HTTP POST /api/v1/users
  -> API handler validates CreateUserRequest (Pydantic)
  -> CreateUserUseCase.execute(CreateUserCommand)
       -> UserRepository (port)
       -> domain validation
  -> API handler maps result to UserResponse
```

### 6.3 Rules

- No business branching in API handlers beyond HTTP concerns.
- Use cases must not import FastAPI `Request` or `Response`.
- Cross-cutting concerns (logging, metrics) wrap at API or middleware level, not inside domain entities.

---

## 7. Dependency Injection Strategy

KYROX Core uses **explicit constructor injection** wired at the API / composition root.

### 7.1 Approach

- FastAPI `Depends()` functions in module `api/dependencies.py` construct use cases with concrete repositories.
- Session lifecycle: `get_db()` from `app.db.session` is injected into repository factories at the API boundary.
- Avoid global singletons for repositories and use cases (except `settings` and shared engine/session factory).

### 7.2 Composition root

- **Primary composition root:** module `api/dependencies.py` and `app/api/v1/router.py`.
- Infrastructure classes are instantiated here, not inside domain or application code.
- Tests override dependencies via FastAPI dependency overrides or explicit constructor injection in unit tests.

### 7.3 Example (illustrative)

```python
def get_create_user_use_case(db: Session = Depends(get_db)) -> CreateUserUseCase:
    repo = SqlAlchemyUserRepository(db)
    return CreateUserUseCase(user_repository=repo)
```

---

## 8. Database Access Rules

- **Only infrastructure** performs SQLAlchemy queries and ORM mutations.
- **Application** opens/commits transactions via unit-of-work pattern or explicit session scope passed from API dependencies—never via hidden globals.
- **Domain** entities are persistence-ignorant.
- ORM models live in `infrastructure/persistence/models/` (or equivalent), separate from domain entities.
- Mappers convert ORM <-> domain at the repository boundary.
- No raw SQL in domain or application unless encapsulated in an infrastructure repository with a documented reason.
- Migrations (Alembic) apply to infrastructure-owned tables only; created when models exist (not in Sprint 0.2.5).

---

## 9. Error Handling Rules

Built on `app.core.exceptions` (Sprint 0.2 foundation).

| Error type | Raised by | HTTP mapping (API) |
|------------|-----------|---------------------|
| `AppException` | Application / domain-friendly wrappers | Configurable status (default 400) |
| Validation errors | Pydantic (API) / domain validators | 422 / 400 |
| Not found | Application use case | 404 via `AppException(status_code=404)` |
| Unauthorized / forbidden | Auth layer (Sprint 0.3+) | 401 / 403 |
| Unexpected errors | Any | 500 via global handler; logged server-side |

### Rules

- Domain raises domain-specific exceptions or returns `Result` types; API/application maps them to HTTP.
- Never leak stack traces or internal details in production responses.
- Log unexpected errors at ERROR level with correlation context (when available).
- API handlers do not catch broad `Exception`; rely on registered global handlers.

---

## 10. DTO and Schema Rules

Three distinct schema categories—**do not merge**:

| Type | Location | Purpose |
|------|----------|---------|
| **API schemas** | `modules/<name>/api/schemas/` | Request/response models for HTTP (Pydantic) |
| **Application DTOs** | `modules/<name>/application/dto/` | Use-case input/output structures |
| **Domain entities** | `modules/<name>/domain/` | Business objects with invariants |

### Rules

- API schemas must not be reused as ORM models.
- Map explicitly: API schema -> command DTO -> domain entity -> response DTO -> API schema.
- Avoid exposing internal IDs or fields products should not see without intent.
- Version API schemas under `/api/v1/`; breaking changes require a new API version.

---

## 11. Testing Strategy

| Layer | Test type | Focus |
|-------|-----------|-------|
| **Domain** | Unit tests | Entities, value objects, domain services; no DB, no HTTP |
| **Application** | Unit tests | Use cases with **fake/in-memory repositories** implementing ports |
| **Infrastructure** | Integration tests | Repositories against real PostgreSQL (test DB) or transactional rollbacks |
| **API** | Integration tests | HTTP contract via `TestClient`; mock or test DB as appropriate |
| **Platform** | Smoke tests | Health endpoint, app startup, quality script |

### Rules

- Tests live under `backend/tests/`, mirroring module structure: `tests/modules/identity/...`.
- No product-specific fixtures in Core tests.
- Tenant isolation tests are mandatory for identity and shared services (Sprint 0.3+).
- Prefer testing use cases directly for business rules; API tests for routing and serialization.
- Run `python scripts/quality_check.py` before opening PRs.

---

## 12. Product Independence Rules

Aligned with [ADR 0001](DECISIONS/0001-core-product-separation.md):

1. **No product code in Core.** FAIR CRM and other products live in separate repositories.
2. **No product domain in Core modules.** CRM entities, pipelines, deals, etc. are forbidden.
3. **No product-specific branching.** Core must not `if product == "fair_crm"` for business behavior.
4. **Neutral APIs.** Core endpoints and permissions use platform language (tenant, user, role)—not CRM vocabulary.
5. **Reusable modules.** Every module under `modules/` must be usable by any KYROX product without modification.
6. **Products integrate via public API** and documented contracts—not by importing Core internal layers.

---

## 13. Compliance Checklist (Pull Requests)

Before merging backend work:

- [ ] Dependencies respect layer import rules (Section 4)
- [ ] No ORM or SQL in domain/application/API (except infra)
- [ ] Use cases exist for non-trivial workflows; API handlers are thin
- [ ] Repository ports defined before SQLAlchemy implementations
- [ ] API schemas separated from domain entities
- [ ] Tests cover the changed layer appropriately
- [ ] No product-specific logic, names in domain models, or FAIR CRM references in code
- [ ] Health endpoint and existing Sprint 0.2 behavior unchanged unless explicitly scoped

---

## 14. Sprint 0.2.5 Status

This document is the **deliverable** for Sprint 0.2.5. Implementation of `modules/identity/` and other layers begins in Sprint 0.3 (Identity Platform).

Existing Sprint 0.2 code (`core/`, `api/v1/health.py`, `db/session.py`) remains valid foundation wiring and will be extended—not replaced—when modules are added.
