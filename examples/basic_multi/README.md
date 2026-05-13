# basic_multi — multi-tenant SaaS example

A multi-tenant adminfoundry app.

## Run

```bash
uvicorn examples.basic_multi.app:app --reload
```

Demo credentials are printed on startup.

### Tenant resolution

Out of the box the example uses **header-based** resolution. Pick the tenant via:

```bash
curl -H "X-Tenant-Slug: acme" http://127.0.0.1:8000/health
```

To run with **subdomain** resolution (`acme.localhost:8000`, `orbit.localhost:8000`),
copy `.env.example` to `.env` and set `TENANT_RESOLUTION_STRATEGY=subdomain`, then
launch uvicorn with `--host 0.0.0.0`.

## What's registered

- `UserAdmin`, `RoleAdmin`, `TenantAdmin`, `AuditLogAdmin` — framework models.
- `ProjectAdmin` — tenant-scoped domain model.

Actions used: `DeactivateUsersAction`, `ActivateUsersAction`, `BulkDeleteAction`,
`DisableTenantAction`, `EnableTenantAction` — all imported from `adminfoundry`.
