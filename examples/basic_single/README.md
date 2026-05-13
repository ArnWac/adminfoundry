# basic_single — single-tenant blog example

A minimal single-tenant adminfoundry app: blog posts + a user admin.

## Run

```bash
uvicorn examples.basic_single.app:app --reload
```

Then visit http://127.0.0.1:8000/admin-ui

Demo credentials are printed on startup. SQLite DB lives in `basic_single.db`.

## What's registered

- `PostAdmin` — list/search/filter, computed fields (`word_count`, `read_time`, `excerpt`), bulk delete action.
- `UserAdmin` — manage users; activate / deactivate / delete actions.
