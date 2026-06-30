"""K3 — tenant-scoped write guard against a missing ``search_path``.

Proves that :func:`assert_tenant_search_path` refuses to run a tenant-scoped
write when ``search_path`` still points at ``public`` (the catastrophic
"forgot SET search_path" case), and is a no-op once a tenant schema is active.
"""

from __future__ import annotations

import pytest

from asterion.tenancy.guard import TenantScopeError, assert_tenant_search_path
from asterion.tenancy.schema_strategy import set_search_path

pytestmark = pytest.mark.postgres


@pytest.mark.asyncio
async def test_guard_raises_on_public_search_path(pg_sessionmaker):
    async with pg_sessionmaker() as session:
        async with session.begin():
            # No SET search_path → defaults to "$user", public.
            with pytest.raises(TenantScopeError):
                await assert_tenant_search_path(session)


@pytest.mark.asyncio
async def test_guard_passes_inside_tenant_schema(pg_schemas, pg_sessionmaker):
    async with pg_sessionmaker() as session:
        async with session.begin():
            await set_search_path(session, pg_schemas["a"])
            # Must not raise once a tenant schema leads the search_path.
            await assert_tenant_search_path(session)
