# basic_single — single-tenant blog example

A minimal single-tenant adminfoundry app: blog posts managed by a global superadmin.

## Run

```bash
uvicorn examples.basic_single.app:app --reload
```

Then visit http://127.0.0.1:8000/admin

Demo credentials are printed to the console on startup. The SQLite database
lives in `basic_single.db`.

## What's registered

- `PostAdmin` — list, search, filter, computed fields (`word_count`,
  `read_time`, `excerpt`), bulk-delete action, two-section form layout.

The tenant RBAC builtins (`TenantRoleAdmin`, etc.) are skipped because this
example sets `enable_multi_tenant=False` and `enable_builtin_admins=False`.

## Seeding

`seed.py` creates one global superadmin (`admin@example.com` / `admin123`)
on every startup. It is idempotent — re-running does not overwrite or
duplicate the user.

You can also seed without booting the server:

```bash
python -m examples.basic_single.seed
```
