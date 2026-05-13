from collections.abc import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from adminfoundry.settings import settings

_engine_kwargs: dict = {"echo": settings.DEBUG}
if "postgresql" in settings.DATABASE_URL:
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True})

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def configure(database_url: str, debug: bool = False) -> None:
    """Reconfigure the database engine from an explicit URL.

    Called by create_admin() when CoreAdminConfig.database_url is set, allowing
    package users to configure the engine without environment variables.
    """
    global engine, AsyncSessionLocal
    kw: dict = {"echo": debug}
    if "postgresql" in database_url:
        kw.update({"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True})
    engine = create_async_engine(database_url, **kw)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def _ensure_configured() -> None:
    """No-op: engine is always initialized eagerly. Kept for API compatibility."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_admin_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Admin-aware DB session.

    When MULTI_TENANT is enabled and a tenant context is present, returns a
    session bound to the tenant engine (search_path = tenant_schema, public).
    Falls back to the shared session otherwise.
    """
    if settings.MULTI_TENANT:
        tenant = getattr(request.state, "tenant", None)
        if tenant is not None:
            from adminfoundry.tenancy.schema_strategy import get_tenant_session
            async for session in get_tenant_session(tenant.schema_name):
                yield session
            return
    async for session in get_db():
        yield session
