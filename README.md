# coreAdmin API

Multi-tenant admin API built with FastAPI, SQLAlchemy async, and Alembic.

## Quick start

```bash
cp .env.example .env
make install
make up
make migrate-shared
uvicorn coreAdmin_api.main:app --reload
```

## Testing

```bash
make test
```
