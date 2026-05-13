# Roadmap — PostgreSQL schema-based multi-tenancy

Status: **planned next milestone**. Not yet covered by integration tests.

## Goal

Provide true tenant data isolation by giving each tenant its own PostgreSQL schema, while keeping a shared schema for cross-tenant entities (users, roles, tenants, audit log).

## What exists today

- `TenantMiddleware` resolves the active tenant from subdomain or `X-Tenant-Slug` header into `request.state.tenant` (a `TenantContext`).
- `adminfoundry.tenancy.schema_strategy` exposes a per-schema engine cache (`get_or_create_tenant_engine`) and a session factory (`get_tenant_session`). The cache validates schema names against an allowlist regex and quotes them in `SET search_path`.
- `get_admin_db()` dispatches to a tenant-scoped session when `MULTI_TENANT=true` and a tenant is present on the request.
- `alembic_shared.ini` exists and is used for the shared schema.
- `alembic_tenant.ini` exists but the tenant migrations directory is skeletal.
- `adminfoundry tenant migrate <slug>` creates a PostgreSQL schema but does not yet stamp/run tenant-scoped Alembic migrations.

## Current limitations

- Tests run against SQLite, which has no schemas. The schema strategy is exercised in unit tests (`test_tenancy_package.py`) but never against real PostgreSQL.
- No CI job runs a real PostgreSQL service.
- No automated isolation test verifies that a query inside tenant A cannot read tenant B's rows when both live in distinct schemas.
- `adminfoundry tenant migrate <slug>` does not run Alembic against the new schema — schema creation works, but the table schema must currently be populated by other means (manual `CREATE TABLE`, `Base.metadata.create_all`, etc.).
- Row-level multi-tenancy (filtering by `tenant_id`) and schema-level multi-tenancy coexist; the policy for which strategy a given model uses is not documented.

## Milestone scope

1. **Alembic for tenant schemas** — flesh out `migrations/tenant/` with the same models as the shared schema minus the shared-only ones (User, Role, Tenant, AuditLog). Wire `adminfoundry tenant migrate <slug>` to run `alembic -c alembic_tenant.ini -x schema=tenant_<slug> upgrade head`.
2. **Integration test job** — CI service container for PostgreSQL 16. New tests file `tests/integration/test_pg_schema_tenancy.py`:
   - Create 2 tenants via the API.
   - Insert tenant-scoped rows for each.
   - Verify a session bound to tenant A's schema sees only A's rows.
   - Verify `SET search_path` cannot be SQL-injected via a tenant slug.
3. **Schema seeding hook** — on tenant creation, run `alembic upgrade head` against the new schema in a single transaction. Roll back on failure.
4. **Docs** — concrete instructions for production deployments: PG roles per tenant (optional), search_path security, schema name allowlist, and how to migrate when a new model is added.

## Non-goals for this milestone

- Per-tenant database (separate DB, not separate schema).
- Cross-tenant search.
- Schema-aware UI (the UI already routes via subdomain; no UI change is required).

## Tracking

This file is the single source of truth for the milestone scope. When work starts, link the issue / branch here.
