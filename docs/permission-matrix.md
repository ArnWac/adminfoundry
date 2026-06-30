# Permission matrix

The default role → permission-key mapping, how keys are shaped, and how the
catalog is generated. Source of truth in code:
[`asterion/authz/catalog.py`](../asterion/authz/catalog.py) and
[`asterion/tenancy/bootstrap.py`](../asterion/tenancy/bootstrap.py).

## Permission keys

A key is `admin.<resource>.<action>`. Wildcards are allowed **only** at the
trailing segment (`admin.*`, `admin.posts.*`); middle wildcards are rejected on
parse. The matcher is wildcard-aware — see
[security.md](security.md#authorization).

For every registered resource the catalog generates the five default CRUD
actions plus one key per declared custom admin action:

```
admin.<resource>.{list, read, create, update, delete}      # DEFAULT_CRUD_ACTIONS
admin.<resource>.<custom_action>                            # per @action
```

Extensions contribute their own namespaced keys (e.g.
`oauth.identities.list`). The catalog is populated via
`asterion permissions sync`; tenant bootstrap seeds roles from it.

## Default tenant roles

Three system roles are seeded per tenant
([`bootstrap.py`](../asterion/tenancy/bootstrap.py), `_DEFAULT_ROLE_DEFS`):

| Role | Grants | Rule |
|---|---|---|
| **owner** | `admin.*` **+ every catalog key** | Full tenant access. Always at least `admin.*`. |
| **admin** | Every catalog key **except** the deny list | `_ADMIN_PERMISSIONS_DENY` = `admin.audit_logs.delete`, `admin.users.delete` |
| **viewer** | Every catalog key ending in `.list` | Read-only (list) access. |

So out of the box:

| Action (example resource `posts`) | owner | admin | viewer |
|---|:--:|:--:|:--:|
| `admin.posts.list` | ✅ | ✅ | ✅ |
| `admin.posts.read` | ✅ | ✅ | ❌ |
| `admin.posts.create` | ✅ | ✅ | ❌ |
| `admin.posts.update` | ✅ | ✅ | ❌ |
| `admin.posts.delete` | ✅ | ✅ | ❌ |
| `admin.audit_logs.delete` | ✅ | ❌ (denied) | ❌ |
| `admin.users.delete` | ✅ | ❌ (denied) | ❌ |

Seeding is **idempotent** — re-running bootstrap only adds missing rows. Custom
roles are created and granted through the tenant RBAC UI / API.

## Global (root) scope

Global resources — `users`, `tenants`, `audit_logs`, `impersonation_logs`,
`tenant_memberships` — are **not** governed by tenant roles. They are
**superadmin-only** (`User.is_superadmin`); impersonation tokens are rejected at
root routes. A least-privilege global "Support" role is roadmap **G14**.

With no tenant context (single-tenant / root scope) and no role system to gate
by, the admin surface requires a superadmin by default
(`single_tenant_require_superadmin`, default `True`).

## Regenerating this matrix

The role→key seeding is data-driven from the catalog, so the concrete keys for
*your* deployment depend on your registered resources. Inspect them with:

```bash
asterion permissions sync     # populate / refresh PermissionCatalog
asterion permissions list     # list catalog keys (resource × action)
```

## See also

- [security.md — Authorization](security.md#authorization)
- [tenancy.md](tenancy.md) — tenant RBAC tables and resolution.
- [model-admin.md](model-admin.md) — declaring resources, actions, policies.
