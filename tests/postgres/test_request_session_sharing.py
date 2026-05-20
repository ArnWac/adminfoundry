"""TenantAuthContext and CRUD must operate on the same request session.

The plan requires the request-scoped session to be shared between
``TenantAuthContext`` loading and CRUD operations so a single
``SET LOCAL search_path`` covers both.

We prove this by:
1. Setting search_path on a session
2. Writing tenant-local data (simulates CRUD writing through the same
   session that loaded the auth context)
3. Asserting the write landed in the expected schema
4. Reading from the other schema and confirming nothing leaked
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text

from adminfoundry.models.tenant_rbac import TenantRole, TenantRolePermission
from adminfoundry.tenancy.schema_strategy import set_search_path

pytestmark = pytest.mark.postgres


@pytest.mark.asyncio
async def test_one_session_serves_authz_load_and_crud_write(
    pg_schemas,
    pg_sessionmaker,
):
    """Simulate the dependency chain: require_tenant_auth_context loads
    permission_keys, then the CRUD endpoint writes inside the same
    transaction. Both must land in tenant_a."""
    async with pg_sessionmaker() as session:
        async with session.begin():
            await set_search_path(session, pg_schemas["a"])

            # Step 1: simulate TenantAuthContext loading roles + permissions
            session.add(TenantRole(name="owner", description="o", is_system=True))
            await session.flush()
            role = (
                await session.execute(select(TenantRole).where(TenantRole.name == "owner"))
            ).scalar_one()
            session.add(TenantRolePermission(role_id=role.id, permission_key="admin.*"))

            # Step 2: simulate CRUD adding more rows in the same txn
            session.add(TenantRole(name="viewer", description="v", is_system=True))

    # Verify both rows landed in tenant_a
    async with pg_sessionmaker() as session:
        async with session.begin():
            await set_search_path(session, pg_schemas["a"])
            names = {r.name for r in (await session.execute(select(TenantRole))).scalars().all()}
            assert names == {"owner", "viewer"}

    # Tenant B sees nothing — the shared session did not accidentally
    # write to public or to tenant_b.
    async with pg_sessionmaker() as session:
        async with session.begin():
            await set_search_path(session, pg_schemas["b"])
            names = {r.name for r in (await session.execute(select(TenantRole))).scalars().all()}
            assert names == set()


@pytest.mark.asyncio
async def test_get_tenant_session_helper_yields_scoped_session(
    pg_schemas,
    pg_engine,
):
    """``get_tenant_session(schema, db)`` is the out-of-request helper used
    by the bootstrap CLI. It should yield a session that has search_path
    set to the tenant schema."""
    from adminfoundry.tenancy.schema_strategy import get_tenant_session

    class _DbStub:
        engine = pg_engine

    seen_paths: list[str] = []
    async for session in get_tenant_session(pg_schemas["a"], _DbStub()):
        result = await session.execute(text("SHOW search_path"))
        seen_paths.append(result.scalar_one())
        session.add(TenantRole(name="from-helper", description="h", is_system=False))

    assert seen_paths and pg_schemas["a"] in seen_paths[0]

    # Verify the helper actually committed
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            await set_search_path(session, pg_schemas["a"])
            names = {r.name for r in (await session.execute(select(TenantRole))).scalars().all()}
            assert "from-helper" in names
