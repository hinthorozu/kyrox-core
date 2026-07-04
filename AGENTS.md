# AGENTS.md

Guidance for AI agents and automation working in the `kyrox-core` repository.

## Repository Role

`kyrox-core` is the reusable KYROX SaaS platform service. It owns shared platform capabilities such as authentication, authorization, organizations, memberships, audit, settings, background jobs, notifications, and future product-agnostic infrastructure.

It is not a CRM repository and must not contain product domain logic.

## Repository Boundaries

| Repository | Responsibility |
|------------|----------------|
| `kyrox-platform` | Ecosystem strategy, roadmap, ADRs, status, milestones |
| `kyrox-core` | Reusable SaaS platform services |
| `fair-crm` | CRM product domain, product UI, product database, data integration workflows |

Products consume Core through public HTTP APIs and documented contracts. Core never imports product repositories and never depends on product code.

## Required Reading

Before architecture-sensitive work, read:

1. `README.md`
2. `docs/ROADMAP.md`
3. `CHANGELOG.md`
4. `docs/KYROX_CORE_ARCHITECTURE.md`
5. `docs/BACKEND_ARCHITECTURE_STANDARDS.md`
6. Relevant ADRs under `docs/DECISIONS/`
7. `docs/PRODUCT_INTEGRATION_GUIDE.md` for product-integration work

## Current Platform State

- Current release: v0.4.0
- Platform baseline: completed
- Alembic head: `20260701_0025`
- Test count: 307 passed, 1 skipped
- Repository mode: frozen except bug fixes, security fixes, performance fixes, and CRM-driven reusable platform needs

Product integration APIs are available for authorization checks and audit event writes. Core remains product-agnostic.

## Architecture Rules

- Keep domain/application/infrastructure/api layering consistent with the backend standards.
- Platform modules must be reusable across products.
- Do not add CRM entities, CRM workflows, adapter logic, import pipeline logic, or product UI behavior.
- Product permission records may live in Core RBAC when needed for authorization, but CRM business behavior must stay in the product repository.
- Products integrate through public HTTP APIs; do not create Python package coupling with product repositories.
- Do not share product databases or product SQLAlchemy sessions.

## Change Rules

- During FAIR CRM M4, only change Core for bug fixes, security fixes, performance fixes, or reusable platform needs.
- If a requested feature is product-specific, document that it belongs in `fair-crm`.
- If a requested capability is platform-generic, document the contract and keep it product-neutral.
- Update existing canonical documents instead of creating duplicate roadmap or rule files.

## Verification

For code changes, run verification proportional to the change. For documentation-only changes, do not run backend tests unless the user asks or the documentation change affects documented commands/contracts.

## Git Safety

- Do not commit or push unless the user explicitly approves.
- Never revert user changes unless explicitly requested.
- Keep generated artifacts and local data out of commits.
