"""Base class for an adminfoundry extension.

An :class:`AdminExtension` is the supported way to bundle optional
functionality (routes, permissions, contract fragments, navigation,
protected fields, startup/shutdown hooks) into the framework.

The lifecycle, in order, called by ``create_admin()``:

1. ``configure(config)`` — synchronous validation pass. Extensions
   raise here if config is wrong (missing keys, conflicting flags).
2. ``register_permissions(ctx.permissions)``
3. ``register_protected_fields(ctx.protected_fields)``
4. ``register_contract_contributions(ctx.contract)``
5. ``register_navigation(ctx.navigation)``
6. ``register_routes(app, ctx)`` — only step that gets ``app``.
7. **Framework freezes all registries.**
8. Lifespan starts: ``startup(app)`` called per extension, in
   registration order.
9. Requests served.
10. Lifespan ends: ``shutdown(app)`` called per extension, in REVERSE
    registration order.

Every hook except the ``name`` attribute has a no-op default — most
extensions implement only one or two methods. Subclasses set the
``name`` class attribute, which is the registry key and must be unique
across all extensions configured on a single app.

Example::

    class ImportExportExtension(AdminExtension):
        name = "import_export"

        def register_routes(self, app, ctx):
            app.include_router(my_router, prefix=ctx.config.admin_api_prefix)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from adminfoundry.core.config import CoreAdminConfig
from adminfoundry.extensions.context import ExtensionContext


class AdminExtension:
    """Concrete base class with no-op defaults.

    Subclass and override only the hooks you need. The class doubles as
    the Protocol — duck-typed objects with the same method signatures
    work just as well, but subclassing is the supported path.
    """

    #: Unique name in the extension registry. Subclasses MUST override.
    name: str = ""

    # ---- configuration / validation ----

    def configure(self, config: CoreAdminConfig) -> None:
        """Synchronous validation pass — raise to abort startup."""

    # ---- registry contributions ----

    def register_permissions(self, registry) -> None:
        """Register namespaced permission keys."""

    def register_protected_fields(self, registry) -> None:
        """Register field names that must never appear in API responses,
        contract metadata, or audit/log output."""

    def register_contract_contributions(self, registry) -> None:
        """Add namespaced fragments to the admin contract."""

    def register_navigation(self, registry) -> None:
        """Add permission-gated nav items to the admin UI."""

    def register_routes(self, app: FastAPI, ctx: ExtensionContext) -> None:
        """Mount routes / sub-routers on ``app``.

        This is the only hook that receives ``app`` directly. Run-time
        routes (CRUD, contract, actions) are mounted by the framework
        AFTER this hook, so extension routes that use a static path
        segment (``/{resource}/_export``) win over the dynamic CRUD
        ``/{resource}/{id}`` route — matching the previous behaviour.
        """

    # ---- lifespan ----

    async def startup(self, app: FastAPI) -> None:
        """Async setup at application startup (after registries are frozen)."""

    async def shutdown(self, app: FastAPI) -> None:
        """Async teardown at application shutdown.

        Failures are logged but do not propagate — one extension's
        broken shutdown must not block the others from running.
        """

    # ---- bookkeeping ----

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Don't enforce ``name`` here — let ExtensionRegistry.register
        # raise with the better error when someone forgets it. This
        # keeps importing the class cheap.

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(f"adminfoundry.extensions.{self.name or self.__class__.__name__}")
