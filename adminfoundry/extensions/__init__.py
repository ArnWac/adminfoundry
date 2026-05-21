"""Adminfoundry extensions — optional, opt-in framework add-ons.

An *extension* is anything callable with the signature::

    def register(
        registry: AdminRegistry,
        app: FastAPI,
        config: CoreAdminConfig,
    ) -> None: ...

Extensions are passed to :func:`adminfoundry.create_admin` via the
``extensions=`` keyword argument and are invoked once during app
construction, AFTER the user's own ``register`` callback and BEFORE the
core router mount (so an extension can register additional routes
without colliding with the dynamic CRUD path).

There is no plugin discovery, no entry-point magic, and no formal
``Extension`` class — extensions are simply modules that expose a
``register`` callable. The user opts in by importing and naming them::

    from adminfoundry import create_admin
    from adminfoundry.extensions.import_export import register as csv_export

    app = create_admin(
        config=config,
        register=register_my_admins,
        extensions=[csv_export],
    )

Design rules for new extensions:

* Single ``register(registry, app, config)`` entry point.
* No imports of other extensions — each extension stands alone.
* Routes that need to win over the dynamic CRUD ``{resource}/{id}`` path
  use a static path segment with a leading underscore (e.g. ``_export``,
  mirroring ``_actions``).
* No new framework-wide configuration. If an extension needs settings,
  it reads them from ``config`` or from its own environment variables.
* Tests live in ``tests/extensions/<name>/``.

What an extension is NOT:

* Not a place for things every admin app needs (those belong in core).
* Not a way to extend the contract — the contract API is intentionally
  closed in v1. Extensions can expose their own endpoints next to it.
* Not a hook into request handling — there are no ``before_request`` or
  ``after_request`` extension hooks. Use FastAPI middleware directly if
  you need that.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from adminfoundry.core.config import CoreAdminConfig
from adminfoundry.registry import AdminRegistry

#: Type alias for the extension callable signature.
Extension = Callable[[AdminRegistry, FastAPI, CoreAdminConfig], None]

__all__ = ["Extension"]
