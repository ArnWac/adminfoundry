"""K3 guard — SQLite is a no-op (no schemas to assert).

The real assertion behaviour is proven against PostgreSQL in
``tests/postgres/test_tenant_write_guard.py``. Here we only pin that the guard
never raises on SQLite, so the audit write path stays unaffected in dev/tests.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from asterion.tenancy.guard import assert_tenant_search_path


@pytest.mark.asyncio
async def test_guard_is_noop_on_sqlite(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'guard.db'}")
    try:
        async with async_sessionmaker(engine)() as session:
            # Returns without raising — SQLite has no search_path / schemas.
            await assert_tenant_search_path(session)
    finally:
        await engine.dispose()
