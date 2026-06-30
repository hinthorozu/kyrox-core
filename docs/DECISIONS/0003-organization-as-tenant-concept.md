# ADR 0003: Organization as Tenant Concept

| Field | Value |
|-------|--------|
| **Status** | Accepted |
| **Date** | 2026-07-01 |
| **Sprint** | 0.3 — Identity Platform Design |

## Context

KYROX Core is a multi-tenant SaaS platform serving multiple products: **FAIR CRM**, **Stock**, **WhatsApp**, **Warehouse**, and future applications. Each product customer operates within an isolated account boundary where users, roles, and data must not leak across accounts.

Platform engineering commonly uses **tenant** to describe that isolation boundary. However, "tenant" is infrastructure language—it does not describe what customers and product teams actually manage day to day (a company, workspace, or account).

Earlier KYROX documentation mixed "tenant" and "organization" informally. Sprint 0.3 Identity Platform Design requires a single, explicit domain term before any models or APIs are implemented.

## Decision

**Use `Organization` as the primary domain entity name for the account isolation boundary.**

1. **Domain layer, APIs, and admin contracts** use `Organization`, `organization_id`, and organization-scoped permissions.

2. **Tenant** remains valid as an **infrastructure and multi-tenancy term** only:
   - Request context middleware (tenant resolution → `organization_id`)
   - Database row-level isolation documentation
   - Operational runbooks and hosting configuration

3. **Do not** expose `Tenant` as a public API resource name, domain class name, or primary database table name (`tenants`).

4. Infrastructure code may alias internally (e.g. `tenant_id` in logs) but must map to `organization_id` at the domain boundary.

## Why Organization Is the Domain Name

| Reason | Explanation |
|--------|-------------|
| **Product-neutral** | Every KYROX product has "an organization" using the product; not every team thinks in "tenants." |
| **Customer-facing clarity** | Support, sales, and docs can say "organization settings" without translating jargon. |
| **Stable across verticals** | CRM company, warehouse operator, messaging team, and stock trading desk all map to Organization. |
| **Industry alignment** | B2B SaaS commonly models accounts as organizations/workspaces; tenant is the implementation detail. |
| **API longevity** | `/organizations/{id}/...` ages better than `/tenants/{id}/...` in public integrations. |

## Why Tenant Is Infrastructure Language, Not Primary Business Language

Multi-tenancy describes **how** the platform isolates data (shared schema + `organization_id`, connection routing, etc.). It does not describe **what** the customer manages.

Keeping tenant at the infrastructure layer:

- Avoids leaking database-centric naming into domain models and REST contracts
- Lets engineers discuss "tenant isolation" in architecture reviews while product code speaks Organization
- Prevents a second concept (Tenant vs Organization) in the mental model

**Mapping:**

```text
Business concept:  Organization (domain entity)
Isolation key:     organization_id (every org-scoped row)
Infra term:        tenant context = resolved organization_id on the request
```

## Support for Current and Future Products

| Product | How Organization applies |
|---------|---------------------------|
| **FAIR CRM** | One CRM account per organization; sales users are members with CRM roles assigned via Core RBAC |
| **Stock** | Trading desk or brokerage firm as organization; traders are members |
| **WhatsApp** (product) | Business messaging account as organization; agents are members |
| **Warehouse** | Warehouse operator or 3PL company as organization; staff are members |
| **Future SaaS** | Same identity primitives; product-specific permissions extend the permission namespace |

None of these products require a CRM-specific or channel-specific name for the account boundary. Organization is the shared KYROX account primitive.

Products continue to own **their** domain (deals, SKUs, messages, bins). Core owns **who** belongs to **which organization** and **what platform permissions** they hold.

## Consequences

### Positive

- Consistent identity vocabulary across all KYROX products and documentation
- Clear ADR for reviewers rejecting `Tenant` entity classes in Core domain code
- Public APIs suitable for integration partners without infra jargon
- Aligns with [Identity Platform Design](../IDENTITY_PLATFORM_DESIGN.md) entity model

### Negative / Trade-offs

- Engineers must remember tenant (infra) vs organization (domain) mapping
- Existing docs mentioning "tenant" require gradual alignment (architecture docs may still say "multi-tenant platform")
- Database column naming must standardize on `organization_id` even when discussing "tenant isolation"

## Compliance

From Sprint 0.3.1 implementation onward:

- Domain entities: `Organization`, not `Tenant`
- Tables: `identity_organizations`, not `identity_tenants`
- API paths: `/organizations/...`, not `/tenants/...`
- Permission scoping: organization-scoped, documented as such
- Infrastructure comments may reference multi-tenancy but must map to `organization_id`

Reject pull requests that introduce `Tenant` as a primary domain model without ADR amendment.

## Related Documents

- [Identity Platform Design](../IDENTITY_PLATFORM_DESIGN.md)
- [ADR 0001: Core / Product Separation](0001-core-product-separation.md)
- [ADR 0002: Backend Layered Architecture](0002-backend-layered-architecture.md)
- [Backend Architecture Standards](../BACKEND_ARCHITECTURE_STANDARDS.md)
- [Roadmap](../ROADMAP.md)
