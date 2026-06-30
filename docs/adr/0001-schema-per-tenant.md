# ADR-0001 — Schema-per-tenant instead of Row-Level Security

**Status:** Accepted

## Context

A multi-tenant admin framework must isolate one tenant's data from another's.
The common options:

1. **Discriminator column** (`tenant_id` on every row, filtered in every query).
   Isolation depends on every query remembering the filter — one forgotten
   `WHERE tenant_id = ?` leaks data. The failure mode is silent.
2. **Row-Level Security (RLS)** — Postgres policies enforce `tenant_id` at the
   engine. Strong, but couples every table to a `tenant_id` column and a policy,
   and interacts subtly with connection pooling and the app's own roles.
3. **Schema-per-tenant** — each tenant's operational tables live in their own
   PostgreSQL schema (`tenant_<slug>`), selected per transaction with
   `SET LOCAL search_path`.

The first customer (Simpletimes) handles employee/working-time data where a
cross-tenant leak is a serious incident, so the isolation guarantee needs to be
**structural**, not a discipline every query must uphold.

## Decision

Use **schema-per-tenant** as the isolation mechanism. Tenant tables carry **no**
`tenant_id` column; the schema *is* the tenant. Global tables use an explicit
`public.` qualifier. The request session sets `SET LOCAL search_path` to the
resolved tenant schema for the whole transaction (it evaporates on
commit/rollback, so no state leaks onto the next pooled request). A write guard
(`assert_tenant_search_path`, K3) refuses a tenant-scoped write when the
`search_path` still points at `public`.

Isolation is verified in CI against a **real PostgreSQL** server
(`tests/postgres/`) over the HTTP path — SQLite cannot prove it (no schemas).

## Consequences

- **Positive:** no `tenant_id` filter to forget; isolation is structural; a
  tenant's data is physically grouped (easy per-tenant export/offboard); the
  isolation guarantee is testable end-to-end.
- **Negative:** SQLite (dev/tests) cannot reproduce isolation, so the proof lives
  only in the Postgres suite; asyncpg's prepared-statement cache must be disabled
  for `search_path` switching (`db_statement_cache_size`); schema count scales
  with tenant count (fine for B2B SaaS, not for millions of end-user "tenants").
- **Non-goal:** row-level (per-end-user) tenancy. RLS as an *additional*
  defence-in-depth layer behind schema isolation is deferred to a future ADR
  (roadmap G15) — it would be additive, never a replacement.

See [tenancy.md](../tenancy.md) and [THREAT_MODEL.md](../THREAT_MODEL.md).
