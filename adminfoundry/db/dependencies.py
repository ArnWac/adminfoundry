from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_async_session(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """Return one request-scoped AsyncSession inside one transaction.

    TenantAuthContext and CRUD must use this same dependency so that
    SET LOCAL search_path applies to the CRUD query path.
    """
    runtime = request.app.state.adminfoundry

    async with runtime.db.session() as session:
        async with session.begin():
            yield session
