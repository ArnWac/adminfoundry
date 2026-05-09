# adminfoundry

FastAPI admin framework with built-in UI, JWT auth, RBAC, and optional multi-tenancy.

Register your SQLAlchemy models and get a full admin interface — list, detail, create, edit, delete, bulk actions, audit log, dark mode, and more. No frontend tooling required.

## Install

```bash
# PostgreSQL
pip install adminfoundry[postgres]

# SQLite (development / testing)
pip install adminfoundry[sqlite]
```

## Quickstart

```python
from fastapi import FastAPI
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from adminfoundry import create_coreadmin, CoreAdminConfig, ModelAdmin, admin_site
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

admin_site.register(ArticleAdmin())

app = FastAPI()
create_coreadmin(app, config=CoreAdminConfig(
    default_language="en",
    default_date_format="iso",
))
```

Create a superadmin and start the server:

```bash
adminfoundry create-superadmin
uvicorn myapp:app --reload
```

Open `http://localhost:8000/admin-ui`.

---

## Configuration

Non-secret framework config goes in `pyproject.toml`:

```toml
[tool.adminfoundry]
default_language     = "de"
default_date_format  = "eu"
default_show_timezone = true
enable_multi_tenant  = false
```

Read it with:

```python
config = CoreAdminConfig.from_pyproject()
create_coreadmin(app, config=config)
```

Secrets go in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/mydb
SECRET_KEY=your-random-secret-min-32-chars
```

---

## Pluggable auth

Bring your own auth by subclassing `AuthProvider`:

```python
from adminfoundry import AuthProvider, CoreAdminConfig, create_coreadmin

class MyAuthProvider(AuthProvider):
    async def authenticate(self, request, token, db):
        user = await my_system.verify(token)
        if not user:
            raise HTTPException(401)
        return user

    def is_superadmin(self, user) -> bool:
        return user.is_staff

create_coreadmin(app, config=CoreAdminConfig(
    auth_provider=MyAuthProvider(),
    include_auth_routes=False,  # skip built-in login/logout routes
))
```

---

## Multi-tenancy

```python
create_coreadmin(app, config=CoreAdminConfig(
    enable_multi_tenant=True,
))
```

Tenant resolution via `X-Tenant-Slug` header (default) or subdomain (`TENANT_RESOLUTION_STRATEGY=subdomain` in `.env`).

Mark models as tenant-scoped:

```python
class ProjectAdmin(ModelAdmin):
    model         = Project
    tenant_scoped = True
```

---

## Locale hierarchy

Settings resolve in this order — most specific wins:

```
User preference (browser) → Tenant settings (DB) → CoreAdminConfig default
```

Set tenant language and timezone in the admin UI. Users override in their personal settings page.

---

## Key environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | SQLAlchemy async DB URL |
| `SECRET_KEY` | — | JWT signing key — **required in production** |
| `MULTI_TENANT` | `false` | Enable multi-tenancy |
| `TENANT_RESOLUTION_STRATEGY` | `header` | `header` or `subdomain` |
| `ENABLE_BUILTIN_ADMIN_UI` | `true` | Mount the built-in admin panel |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

---

## CLI

```bash
adminfoundry create-superadmin   # create the first superadmin
adminfoundry doctor              # check DB connection, registry, config
adminfoundry inspect-registry    # list registered models
```

---

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

---

## Examples

- [`examples/blog/`](examples/blog/app.py) — minimal single-tenant app with SQLite

## Requirements

- Python 3.11+
- FastAPI 0.111+
- SQLAlchemy 2.0+

## License

MIT
