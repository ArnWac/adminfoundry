from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from adminfoundry.builtins import install_builtin_admins
from adminfoundry.core.config import CoreAdminConfig
from adminfoundry.core.errors import register_error_handlers
from adminfoundry.core.installers import install_middleware, install_routes
from adminfoundry.core.logging import configure_logging
from adminfoundry.core.runtime import AdminRuntime
from adminfoundry.db.session import DatabaseManager
from adminfoundry.registry import AdminRegistry


def create_admin(
    config: CoreAdminConfig | None = None,
    *,
    register: Callable[[AdminRegistry], None] | None = None,
    **fastapi_kwargs,
) -> FastAPI:
    config = config or CoreAdminConfig.from_env()
    config.validate()

    configure_logging(config)

    app = FastAPI(
        title=config.app_title,
        debug=config.debug,
        **fastapi_kwargs,
    )

    runtime = AdminRuntime(
        config=config,
        db=DatabaseManager(
            config.database_url,
            echo=config.debug,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_pre_ping=config.db_pool_pre_ping,
        ),
    )

    app.state.adminfoundry = runtime

    register_error_handlers(app)
    install_middleware(app, config)

    if config.enable_builtin_admins:
        install_builtin_admins(runtime.registry)

    if register is not None:
        register(runtime.registry)

    install_routes(app, config)

    return app
