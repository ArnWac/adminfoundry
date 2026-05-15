"""V1 factory + runtime contract tests.

Enforces:
- create_admin() is factory-only — no app= parameter
- create_admin() returns a fresh FastAPI instance
- AdminRuntime is attached to app.state.adminfoundry
- Two apps are isolated (no shared runtime / registries)
- AdminRuntime has all required fields
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI

from adminfoundry import CoreAdminConfig, create_admin
from adminfoundry.admin.dashboard.registry import DashboardRegistry
from adminfoundry.auth_provider import AuthProvider
from adminfoundry.core.events import EventBus
from adminfoundry.core.runtime import AdminRuntime, get_runtime
from adminfoundry.extensions import ExtensionRegistry


def test_create_admin_returns_fastapi_app():
    app = create_admin(config=CoreAdminConfig())
    assert isinstance(app, FastAPI)


def test_create_admin_rejects_positional_app_argument():
    """V1: existing-app mounting is not supported. Passing an app positionally must fail."""
    existing = FastAPI()
    with pytest.raises(TypeError):
        create_admin(existing)  # type: ignore[misc]


def test_runtime_attached_to_app_state():
    app = create_admin(config=CoreAdminConfig())
    runtime = get_runtime(app)
    assert isinstance(runtime, AdminRuntime)
    assert app.state.adminfoundry is runtime


def test_runtime_has_v1_fields():
    app = create_admin(config=CoreAdminConfig())
    runtime = app.state.adminfoundry
    assert isinstance(runtime.config, CoreAdminConfig)
    assert isinstance(runtime.auth_provider, AuthProvider)
    assert isinstance(runtime.extension_registry, ExtensionRegistry)
    assert isinstance(runtime.dashboard_registry, DashboardRegistry)
    assert isinstance(runtime.event_bus, EventBus)


def test_two_apps_have_isolated_runtimes():
    app1 = create_admin(config=CoreAdminConfig())
    app2 = create_admin(config=CoreAdminConfig())
    assert app1 is not app2
    assert app1.state.adminfoundry is not app2.state.adminfoundry
    assert (
        app1.state.adminfoundry.extension_registry
        is not app2.state.adminfoundry.extension_registry
    )
    assert (
        app1.state.adminfoundry.dashboard_registry
        is not app2.state.adminfoundry.dashboard_registry
    )


def test_event_bus_per_app():
    """EventBus is fresh per app — handlers do not leak across apps."""
    app1 = create_admin(config=CoreAdminConfig())
    app2 = create_admin(config=CoreAdminConfig())

    async def _h(payload):
        pass

    app1.state.adminfoundry.event_bus.subscribe("evt", _h)
    assert "evt" not in app2.state.adminfoundry.event_bus._handlers


def test_admin_router_module_has_no_factory_logic():
    """admin/router.py is a router aggregator only — create_admin lives in core/app_factory."""
    import adminfoundry.admin.router as r

    assert not hasattr(r, "create_admin")
    assert not hasattr(r, "_admin_config")
    assert hasattr(r, "router")
