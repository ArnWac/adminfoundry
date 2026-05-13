"""
Multi-tenant SaaS example — subdomain-based tenant resolution.

Run:
    uvicorn examples.basic_multi.app:app --reload --host 0.0.0.0

Then visit:
    http://127.0.0.1:8000/admin-ui           (superadmin / root panel)
    http://acme.localhost:8000/admin-ui      (tenant: acme)
    http://orbit.localhost:8000/admin-ui     (tenant: orbit)

*.localhost is resolved to 127.0.0.1 automatically on modern OSes.
"""
import asyncio
from contextlib import asynccontextmanager

import examples.basic_multi.database  # noqa: F401 — set env vars before other imports

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

import examples.basic_multi.admin_config  # noqa: F401 — register admins
from adminfoundry.admin.router import create_admin
from adminfoundry.auth_provider import AuthProvider
from adminfoundry.cleanup import periodic_cleanup
from adminfoundry.core.config import CoreAdminConfig
from adminfoundry.middleware.errors import (
    UnhandledExceptionMiddleware,
    validation_exception_handler,
)
from adminfoundry.middleware.logging import RequestLoggingMiddleware
from adminfoundry.middleware.rate_limit import RateLimitMiddleware
from adminfoundry.middleware.security_headers import SecurityHeadersMiddleware
from adminfoundry.middleware.tenant import TenantMiddleware
from adminfoundry.routers import auth, health, roles, tenants, users
from adminfoundry.settings import settings
from examples.basic_multi.seed import seed, print_banner


config = CoreAdminConfig.from_settings(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed()
    print_banner()
    task = asyncio.create_task(periodic_cleanup())
    try:
        yield
    finally:
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass


app = FastAPI(title="adminfoundry — basic_multi", lifespan=lifespan)
app.state.auth_provider = config.auth_provider or AuthProvider()

app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(tenants.router)

create_admin(app, config=config)

if config.enable_builtin_ui:
    from adminfoundry.routers.admin_ui import router as admin_ui_router, get_static_app
    app.mount(
        f"{settings.ADMIN_UI_PATH}/static",
        get_static_app(),
        name="admin-static",
    )
    app.include_router(admin_ui_router, prefix=settings.ADMIN_UI_PATH)
