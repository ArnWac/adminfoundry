# adminfoundry

adminfoundry is a contract-driven FastAPI admin framework for SQLAlchemy applications. The current focus is a stable core API, predictable admin contracts, and a lightweight built-in UI.

Register your SQLAlchemy models declaratively and get a generated admin: CRUD routes, bulk actions, audit log, role-based access, optional multi-tenant scoping, a built-in lightweight UI, and a renderer-independent contract API for external clients.

---

## Install

```bash
# PostgreSQL
pip install adminfoundry[postgres]

# SQLite (development / testing)
pip install adminfoundry[sqlite]

# Optional extras
pip install adminfoundry[redis]   # Redis cache + rate limiting backend
pip install adminfoundry[s3]      # S3 storage backend
pip install adminfoundry[xlsx]    # Excel (.xlsx) export
```

---

## Quickstart (single-tenant)

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from adminfoundry import (
    create_admin, CoreAdminConfig, ModelAdmin, admin_site,
    BulkDeleteAction,
)
from adminfoundry.models.base import TimestampedBase


class Article(TimestampedBase):
    __tablename__ = "articles"
    title:     Mapped[str]  = mapped_column(String(255))
    published: Mapped[bool] = mapped_column(default=False)


class ArticleAdmin(ModelAdmin):
    model           = Article
    list_display    = ["title", "published", "created_at"]
    search_fields   = ["title"]
    filter_fields   = ["published"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions         = [BulkDeleteAction()]


admin_site.register(ArticleAdmin())

app = create_admin(config=CoreAdminConfig(), title="My Admin")
```

`create_admin()` is a factory: it creates the FastAPI app, installs all core middleware, routers, and the built-in UI, and returns the configured app. Pass an existing app as the first argument to mount AdminFoundry onto it instead.

See [`examples/basic_single/`](examples/basic_single/) for a runnable version.

---

## Register your first model

1. Define a SQLAlchemy model that inherits from `TimestampedBase` (gives you `id`, `created_at`, `updated_at`).
2. Subclass `ModelAdmin` and set `model = YourModel`. Pick `list_display`, `search_fields`, `filter_fields`, `readonly_fields`.
3. Call `admin_site.register(YourAdmin())` at import time.
4. Call `app = create_admin(config=CoreAdminConfig(), title="My Admin")` to get a fully wired app.

### Framework model defaults

`create_admin()` automatically registers sensible admin configurations for the four built-in framework models: **User**, **Role**, **Tenant** (multi-tenant only), and **AuditLog**. You get full CRUD, search, filters, and actions for these with zero configuration.

**Override** a default by registering your own class before calling `create_admin()`:

```python
from adminfoundry import ModelAdmin, admin_site
from adminfoundry.models.user import User
from adminfoundry.actions import DeactivateUsersAction, BulkDeleteAction

class MyUserAdmin(ModelAdmin):
    model       = User
    list_display = ["email", "department", "is_active"]
    extra_create_fields = {"set_password": str}

    @classmethod
    def before_create(cls, data: dict) -> dict:
        from adminfoundry.auth import hash_password
        plain = data.pop("set_password", None)
        if plain:
            data["hashed_password"] = hash_password(plain)
        return data

admin_site.register(MyUserAdmin())   # registered before create_admin() → replaces default
app = create_admin(config=CoreAdminConfig(), title="My Admin")
```

**Add** an app-specific model the same way — framework defaults and your registrations coexist:

```python
admin_site.register(ArticleAdmin())  # app model — added on top of framework defaults
app = create_admin(config=CoreAdminConfig(), title="My Admin")
```

Common attributes:

| Attribute | Purpose |
|-----------|---------|
| `list_display` | Columns shown in list view. |
| `search_fields` | Fields the search box matches against. |
| `filter_fields` | Fields exposed as filters. |
| `readonly_fields` | Fields rejected on create/update. |
| `protected_fields` | Fields excluded from list / detail / contract payloads. |
| `actions` | List of `AdminAction` instances available for bulk/single operations. |
| `tenant_scoped` | If True, list/detail are filtered by the active tenant. |
| `computed_fields` | Dict of `name → callable(obj)` for derived list columns. |

---

## Multi-tenant

```python
from adminfoundry import create_admin, CoreAdminConfig
from adminfoundry.settings import settings

config = CoreAdminConfig.from_settings(settings)
config.enable_multi_tenant = True
config.tenant_resolution = "subdomain"   # or "header" for X-Tenant-Slug

app = create_admin(config=config, title="My SaaS Admin", lifespan=lifespan)
```

`create_admin()` adds `TenantMiddleware` automatically when `enable_multi_tenant=True`. No manual middleware wiring required.

See [`examples/basic_multi/`](examples/basic_multi/) for a runnable subdomain-based SaaS example.

Multi-tenancy ships with two strategies: row-level (every `tenant_scoped` model carries `tenant_id`) and schema-level (one PostgreSQL schema per tenant). Row-level is covered by tests. Schema-level is wired but lacks end-to-end PostgreSQL test coverage — see the roadmap below.

---

## Storage backends

The default storage backend is `LocalStorage("uploads")`. Wire an alternative through `CoreAdminConfig.storage_backend`:

```python
from adminfoundry import create_admin, CoreAdminConfig
from adminfoundry.extensions.storage_s3 import S3Storage

config = CoreAdminConfig(
    storage_backend=S3Storage(bucket="my-bucket", region="eu-central-1"),
)
app = create_admin(config=config)
```

`S3Storage` lives under `adminfoundry/extensions/` because it pulls the optional `boto3` dependency (install via `pip install adminfoundry[s3]`). It is **not** an `ExtensionBase` plugin — provider backends are wired through dedicated config fields rather than `CoreAdminConfig.extensions`. Core never eagerly imports `boto3`.

---

## Feature status

| Stable | Experimental | Planned |
|--------|--------------|---------|
| Registry / `ModelAdmin` | Multi-tenancy (SQLite-tested only) | PostgreSQL schema multi-tenancy (end-to-end) |
| Dynamic schema builder + serializer | Approval workflow (backend only) | SCIM / SAML |
| CRUD routes | Webhooks / signals | Flutter / external UI |
| Contract API (`/api/v1/admin/...`) | Dashboard widgets | Billing / metering |
| Protected field handling | Background jobs extension | White-labeling |
| JWT auth + RBAC | CSV import | Advanced workflow approvals |
| Built-in lightweight UI | Soft delete | |
| Common actions (`adminfoundry.actions`) | Computed fields | |
| Audit log | i18n / locale | |

Stable features have tests and runnable examples. Experimental features work in the happy path but lack one or more of: real-PostgreSQL coverage, end-to-end UI, or stability guarantees across releases.

---

## Roadmap / Next milestone — PostgreSQL schema-based tenancy

The next milestone is full PostgreSQL schema-based multi-tenancy. Scope:

- Shared schema (users, roles, tenants, audit log) and one schema per tenant for domain data.
- Alembic configs for both: `alembic_shared.ini` (exists) and `alembic_tenant.ini` (exists, skeletal).
- Integration tests against a real PostgreSQL service.
- Tenant isolation tests (one tenant cannot read or write rows of another).
- Schema creation + seeding on tenant creation, including initial Alembic stamp.
- Tenant-aware async session factory cached per schema with `search_path` injection-safe.

See [`docs/roadmap-postgres-tenancy.md`](docs/roadmap-postgres-tenancy.md) for the full plan and current limitations.

---

## Examples

| Example | Description |
|---------|-------------|
| [`examples/basic_single/`](examples/basic_single/) | Single-tenant blog: `PostAdmin` with computed fields and bulk delete. Framework model defaults (User, AuditLog, …) require no extra code. |
| [`examples/basic_multi/`](examples/basic_multi/) | Multi-tenant SaaS: tenant-scoped `ProjectAdmin`. Framework defaults cover User, Role, Tenant, and AuditLog automatically. Seeds 1 superadmin + 2 tenants + 2 tenant admins. |

Run them:

```bash
make dev-single   # uvicorn examples.basic_single.app:app
make dev-multi    # uvicorn examples.basic_multi.app:app
```

Both print demo credentials on startup.

---

## Docs

- [Architecture](docs/architecture.md)
- [Tenancy](docs/tenancy.md)
- [Security](docs/security.md)
- [ModelAdmin configuration](docs/model-admin.md)
- [Protected fields](docs/protected-fields.md)
- [Roadmap — PostgreSQL schema tenancy](docs/roadmap-postgres-tenancy.md)

---

## CLI

```bash
adminfoundry init [dir]                 # scaffold a minimal app
adminfoundry create-superadmin          # interactive superadmin creation
adminfoundry create-user                # create a regular user, optionally with a role
adminfoundry seed-roles [--grant-...]   # seed default admin/user roles
adminfoundry inspect-registry           # list registered models + fields + actions
adminfoundry doctor                     # DB connectivity + registry + extensions health
adminfoundry db check                   # check DB connectivity
adminfoundry db upgrade [--env]         # run alembic upgrade head
adminfoundry migrate generate -m "..."  # alembic revision --autogenerate
adminfoundry migrate apply              # alembic upgrade head
adminfoundry migrate status             # current revision + heads
adminfoundry extensions list            # list registered extensions
adminfoundry extensions check           # run startup_check() on each
adminfoundry tenant migrate <slug>      # create PG schema for a tenant
adminfoundry tenant upgrade --all       # run tenant schema migrations for all active tenants
```

`adminfoundry doctor` and `adminfoundry inspect-registry` work without an admin app — but they only see models you have already imported. Run them inside your application's process or after `python -c "import myapp.admin_config"`.

---

## Environment

Key variables (see [`.env.example`](.env.example)):

```
DATABASE_URL=postgresql+asyncpg://...
SECRET_KEY=...
MULTI_TENANT=false
TENANT_RESOLUTION_STRATEGY=header    # or: subdomain
ADMIN_UI_PATH=/admin-ui
```
