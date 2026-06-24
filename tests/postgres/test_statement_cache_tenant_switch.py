"""asyncpg prepared-statement cache vs. schema-per-tenant search_path.

Bug (prod-blocking from the 2nd tenant on): asyncpg keys its server-side
prepared-statement cache by SQL *text*, not by ``search_path``. On a shared
pool, a plan prepared while a connection points at tenant A's schema can be
reused when that same pooled connection later serves tenant B — whose
``employees`` (here ``tenant_roles``) table has a different OID — and postgres
raises ``InvalidCachedStatementError`` (HTTP 500). It is non-deterministic in
production: it depends on which pooled connection a request lands on and how
requests interleave, so with exactly one tenant it never surfaces.

We deliberately do *not* try to assert the 500 here: SQLAlchemy's asyncpg
dialect transparently re-prepares on ``InvalidCachedStatementError`` for
sequential access, so the failure only materialises under concurrency/timing
that a single-threaded test can't pin deterministically (asserting it would be
flaky — verified: sequential cross-schema reuse self-heals).

What we *can* pin is that the fix is wired correctly end to end and is safe:
with the cache disabled (``statement_cache_size=0``, the framework default for
multi-tenant), the *same* ORM select run alternately against two tenant schemas
on a single shared connection (``pool_size=1`` forces cross-schema reuse)
returns correctly isolated per-tenant results with no error. The unit suite
(``tests/operations/test_db_pool.py``) pins the config/engine plumbing that puts
``statement_cache_size=0`` on the Postgres engine for multi-tenant deployments.

Skipped automatically unless ``ASTERION_TEST_POSTGRES_URL`` is set.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select

from asterion.db.session import DatabaseManager
from asterion.models.tenant_rbac import TenantRole
from asterion.tenancy.schema_strategy import set_search_path
from tests.postgres.conftest import _postgres_url

pytestmark = pytest.mark.postgres


@pytest_asyncio.fixture
async def cache_off_db(pg_schemas):
    """A single-connection DatabaseManager with the asyncpg statement cache off,
    with each tenant schema seeded with a distinct role so isolation is
    observable. ``pool_size=1`` guarantees the one connection is reused across
    both schemas — exactly the condition that trips the cache in production.
    """
    url = _postgres_url()
    db = DatabaseManager(url, pool_size=1, statement_cache_size=0)
    for key, role_name in (("a", "role_a"), ("b", "role_b")):
        async with db.session() as s:
            async with s.begin():
                await set_search_path(s, pg_schemas[key])
                s.add(TenantRole(name=role_name, description=role_name, is_system=False))
    try:
        yield pg_schemas, db
    finally:
        await db.dispose()


async def _select_role_names(db, schema) -> set[str]:
    async with db.session() as session:
        async with session.begin():
            await set_search_path(session, schema)
            result = await session.execute(select(TenantRole.name))
            return set(result.scalars().all())


@pytest.mark.asyncio
async def test_cache_off_survives_cross_schema_reuse_with_isolation(cache_off_db):
    """Acceptance: same select, alternating tenants on one pooled connection,
    cache disabled → no error and correctly isolated results per tenant."""
    schemas, db = cache_off_db

    for _ in range(6):
        assert await _select_role_names(db, schemas["a"]) == {"role_a"}
        assert await _select_role_names(db, schemas["b"]) == {"role_b"}
