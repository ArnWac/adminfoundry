"""App installer functions.

Each `install_*` takes `(app, runtime)` and performs one focused setup step.
`create_admin()` orchestrates them in order.

Settings mutation note: `install_state()` still writes a few values back to
`adminfoundry.settings.settings` because deeply-coupled call sites (auth.py
JWT encode/decode, database.py engine, tenancy middleware) read those at module
load time. The canonical source is `runtime.config`; the global settings are
kept in sync as a transitional measure pending a deeper auth/JWT refactor.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from adminfoundry.core.runtime import AdminRuntime


def make_lifespan(user_lifespan, enable_cleanup: bool, cleanup_interval: int):
    """Compose optional periodic cleanup with the user's lifespan."""
    if not enable_cleanup:
        return user_lifespan

    @asynccontextmanager
    async def _cleanup_ctx(app):
        import asyncio
        from adminfoundry.cleanup import periodic_cleanup
        task = asyncio.create_task(periodic_cleanup(interval_seconds=cleanup_interval))
        try:
            yield
        finally:
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    if user_lifespan is None:
        return _cleanup_ctx

    @asynccontextmanager
    async def _composed(app):
        async with user_lifespan(app):
            async with _cleanup_ctx(app):
                yield

    return _composed


def install_state(app: "FastAPI", runtime: "AdminRuntime") -> None:
    from adminfoundry.settings import settings as _settings
    config = runtime.config

    if config.database_url is not None:
        _settings.DATABASE_URL = config.database_url
        import adminfoundry.database as _db
        _db.configure(config.database_url, debug=_settings.DEBUG)
    else:
        import adminfoundry.database as _db
        _db._ensure_configured()

    if config.secret_key is not None:
        _settings.SECRET_KEY = config.secret_key

    if config.user_model is not None:
        from adminfoundry.models.protocols import validate_user_model
        validate_user_model(config.user_model)
        runtime.auth_provider.user_model = config.user_model

    app.state.auth_provider = runtime.auth_provider

    from adminfoundry import cache as _cache_mod, storage as _storage_mod, i18n as _i18n_mod
    if config.cache_backend:
        _cache_mod.configure(config.cache_backend)
    if config.storage_backend:
        _storage_mod.configure(config.storage_backend)
    if config.default_language:
        _i18n_mod.set_default_language(config.default_language)


def install_exception_handlers(app: "FastAPI", runtime: "AdminRuntime") -> None:
    from fastapi.exceptions import RequestValidationError
    from adminfoundry.middleware.errors import validation_exception_handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)


def install_framework_defaults(app: "FastAPI", runtime: "AdminRuntime") -> None:
    from adminfoundry.admin.default_admins import register_framework_defaults
    register_framework_defaults(enable_multi_tenant=runtime.config.enable_multi_tenant)


def install_middleware(app: "FastAPI", runtime: "AdminRuntime") -> None:
    # FastAPI stacks middleware in reverse — first added is innermost (closest to handler).
    from adminfoundry.middleware.errors import UnhandledExceptionMiddleware
    from adminfoundry.middleware.security_headers import SecurityHeadersMiddleware
    from adminfoundry.middleware.rate_limit import RateLimitMiddleware
    from adminfoundry.middleware.logging import RequestLoggingMiddleware
    from adminfoundry.settings import settings as _settings
    config = runtime.config

    app.add_middleware(UnhandledExceptionMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    if config.enable_multi_tenant:
        _settings.MULTI_TENANT = True
        _settings.TENANT_RESOLUTION_STRATEGY = config.tenant_resolution
        from adminfoundry.tenancy.middleware import TenantMiddleware
        app.add_middleware(TenantMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)


def install_core_routers(app: "FastAPI", runtime: "AdminRuntime") -> None:
    from adminfoundry.routers import health, users, roles
    app.include_router(health.router)
    app.include_router(users.router)
    app.include_router(roles.router)
    if runtime.config.include_auth_routes:
        from adminfoundry.routers import auth
        app.include_router(auth.router)
    if runtime.config.enable_multi_tenant:
        from adminfoundry.routers import tenants
        app.include_router(tenants.router)


def install_admin_api(app: "FastAPI", runtime: "AdminRuntime") -> None:
    from adminfoundry.admin.router import router as admin_router
    app.include_router(admin_router)


def install_extensions(app: "FastAPI", runtime: "AdminRuntime") -> None:
    """Register extensions on the per-app runtime.

    Module-level `extension_registry` and `dashboard_registry` singletons are also
    refreshed for CLI/inspection use (e.g. `adminfoundry extensions list`). In a
    multi-app process they reflect the most recent app — request handlers must
    always read from `request.app.state.adminfoundry.{name}_registry` instead.
    """
    from adminfoundry.admin.dashboard.builtins import DEFAULT_WIDGETS
    from adminfoundry.admin.dashboard.registry import dashboard_registry as _legacy_dashboard
    from adminfoundry.extensions import extension_registry as _legacy_ext
    config = runtime.config

    if config.dashboard_widgets is not None and config.dashboard_widgets_mode == "replace":
        base = list(config.dashboard_widgets)
    elif config.dashboard_widgets is not None:
        base = list(DEFAULT_WIDGETS) + list(config.dashboard_widgets)
    else:
        base = list(DEFAULT_WIDGETS)
    runtime.dashboard_registry.reset(base=base)
    _legacy_dashboard.reset(base=base)

    _legacy_ext._extensions.clear()
    for ext in config.extensions:
        runtime.extension_registry.register(ext)
        _legacy_ext.register(ext)
        ext.get_models()  # import side-effect registers extension tables with Base.metadata
        for ext_router in ext.get_routers():
            app.include_router(ext_router)
        for w in ext.get_dashboard_widgets():
            runtime.dashboard_registry.register(w)
            _legacy_dashboard.register(w)


def install_builtin_ui(app: "FastAPI", runtime: "AdminRuntime") -> None:
    from adminfoundry.routers import admin_ui as _admin_ui_module
    from adminfoundry.settings import settings as _settings
    config = runtime.config

    _admin_ui_module._locale_defaults = {
        "language": config.default_language,
        "date_format": config.default_date_format,
        "date_pattern": config.default_date_pattern,
        "show_timezone": config.default_show_timezone,
    }
    _admin_ui_module._extra_i18n = config.extra_i18n

    if config.enable_builtin_ui:
        from adminfoundry.routers.admin_ui import router as admin_ui_router, get_static_app
        ui_path = _settings.ADMIN_UI_PATH
        app.mount(f"{ui_path}/static", get_static_app(), name="admin-static")
        app.include_router(admin_ui_router, prefix=ui_path)


def install_audit(app: "FastAPI", runtime: "AdminRuntime") -> None:
    from adminfoundry.routers.audit import router as audit_router
    app.include_router(audit_router)
    # Audit middleware is always active — core infrastructure, not optional
    from adminfoundry.middleware.audit import AuditMiddleware
    app.add_middleware(AuditMiddleware)
