"""App factory — owns `create_admin()`.

Factory-only: always creates and returns a new FastAPI app. Existing-app
mounting is not supported in V1.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_admin(
    *,
    config=None,
    title: str | None = None,
    lifespan=None,
    **fastapi_kwargs,
) -> "FastAPI":
    """Create and return a fully configured FastAPI admin app.

    Example::

        from adminfoundry import create_admin, CoreAdminConfig

        app = create_admin(
            config=CoreAdminConfig.from_settings(settings),
            title="My Admin",
        )

    ``config`` must be passed as a keyword argument. To mount adminfoundry
    onto an existing FastAPI app, use a separate `mount_admin()` API (not yet
    implemented in V1).
    """
    from fastapi import FastAPI
    from adminfoundry.admin.dashboard.registry import DashboardRegistry
    from adminfoundry.auth_provider import AuthProvider
    from adminfoundry.core.config import CoreAdminConfig
    from adminfoundry.core.events import EventBus
    from adminfoundry.core.installers import (
        install_admin_api,
        install_audit,
        install_builtin_ui,
        install_core_routers,
        install_exception_handlers,
        install_extensions,
        install_framework_defaults,
        install_middleware,
        install_state,
        make_lifespan,
    )
    from adminfoundry.core.runtime import AdminRuntime
    from adminfoundry.extensions import ExtensionRegistry
    from adminfoundry.settings import settings as _settings

    config = config or CoreAdminConfig()

    effective_lifespan = make_lifespan(
        lifespan,
        _settings.ENABLE_CLEANUP_TASK,
        _settings.CLEANUP_INTERVAL_SECONDS,
    )
    app = FastAPI(title=title or "adminfoundry", lifespan=effective_lifespan, **fastapi_kwargs)

    runtime = AdminRuntime(
        config=config,
        auth_provider=config.auth_provider or AuthProvider(),
        extension_registry=ExtensionRegistry(),
        dashboard_registry=DashboardRegistry(),
        event_bus=EventBus(),
    )
    app.state.adminfoundry = runtime

    install_state(app, runtime)
    install_exception_handlers(app, runtime)
    install_middleware(app, runtime)
    install_framework_defaults(app, runtime)
    install_core_routers(app, runtime)
    install_extensions(app, runtime)  # before admin API so extension routes win over /{model_name}
    install_admin_api(app, runtime)
    install_builtin_ui(app, runtime)
    install_audit(app, runtime)

    return app
