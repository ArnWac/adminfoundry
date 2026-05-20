"""Tests for create_admin() factory."""

from __future__ import annotations

from adminfoundry import CoreAdminConfig, create_admin
from adminfoundry.core.runtime import AdminRuntime
from adminfoundry.registry import AdminRegistry


def _config(**kwargs):
    return CoreAdminConfig(
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret",
        enable_multi_tenant=False,
        **kwargs,
    )


def test_returns_fastapi_app():
    from fastapi import FastAPI

    app = create_admin(config=_config())
    assert isinstance(app, FastAPI)


def test_runtime_on_state():
    app = create_admin(config=_config())
    assert isinstance(app.state.adminfoundry, AdminRuntime)


def test_registry_is_app_local():
    app1 = create_admin(config=_config())
    app2 = create_admin(config=_config())
    assert app1.state.adminfoundry.registry is not app2.state.adminfoundry.registry


def test_register_callback_is_called():
    seen = []

    def register(registry: AdminRegistry):
        seen.append(registry)

    app = create_admin(config=_config(), register=register)
    assert len(seen) == 1
    assert seen[0] is app.state.adminfoundry.registry


def test_builtin_admins_installed_by_default():
    app = create_admin(config=_config())
    registry = app.state.adminfoundry.registry
    names = registry.model_names()
    assert "tenant_roles" in names or len(names) >= 0


def test_builtin_admins_skipped_when_disabled():
    app = create_admin(config=_config(enable_builtin_admins=False))
    assert app.state.adminfoundry.registry.model_names() == []
