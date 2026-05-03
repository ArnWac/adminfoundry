from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from coreAdmin_api.settings import settings
from coreAdmin_api.routers import auth, health, users, roles, tenants
from coreAdmin_api.routers import audit
from coreAdmin_api.routers import break_glass
from coreAdmin_api.middleware.errors import validation_exception_handler, UnhandledExceptionMiddleware
from coreAdmin_api.middleware.logging import RequestLoggingMiddleware
from coreAdmin_api.middleware.tenant import TenantMiddleware
from coreAdmin_api.middleware.audit import AuditMiddleware
from coreAdmin_api.admin.router import create_coreadmin
import coreAdmin_api.admin_config  # noqa: F401 — trigger admin registrations

app = FastAPI(title="coreAdmin API")

app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(tenants.router)
app.include_router(audit.router)
app.include_router(break_glass.router)
create_coreadmin(app)

if settings.ENABLE_BUILTIN_ADMIN_UI:
    from coreAdmin_api.routers.admin_ui import router as admin_ui_router, get_static_app
    # Mount static BEFORE router so /static/* isn't swallowed by /{model_name}
    app.mount(
        f"{settings.ADMIN_UI_PATH}/static",
        get_static_app(),
        name="admin-static",
    )
    app.include_router(admin_ui_router, prefix=settings.ADMIN_UI_PATH)
