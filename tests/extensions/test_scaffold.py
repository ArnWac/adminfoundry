"""Tests for the AdminExtension SPI itself (Phase 5).

Verifies the formal class-based extension contract:

* ``AdminExtension`` requires a non-empty ``name``.
* ``ExtensionRegistry`` rejects duplicates and freezes.
* The lifecycle calls every ``register_*`` hook in the documented order
  before mounting core routes.
* Extension routes win over the dynamic CRUD ``/{resource}/{id}`` route.
* Extension contributions land in the right runtime registries.
* Registries are frozen after setup — attempts to mutate them later
  raise ``RegistryFrozenError``.
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

from adminfoundry import CoreAdminConfig, ModelAdmin, create_admin
from adminfoundry.extensions import (
    AdminExtension,
    DuplicateExtensionError,
    ExtensionContext,
    ExtensionRegistry,
    RegistryFrozenError,
)
from adminfoundry.security.protected_fields import reset_for_tests as reset_protected


class _Base(DeclarativeBase):
    pass


class Thing(_Base):
    __tablename__ = "scaffold_things"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)


class ThingAdmin(ModelAdmin):
    model = Thing


@pytest.fixture(autouse=True)
def _isolate_protected_fields():
    """Phase 4's ProtectedFieldRegistry is a singleton — reset between tests."""
    reset_protected()
    yield
    reset_protected()


def _config(tmp_path) -> CoreAdminConfig:
    return CoreAdminConfig(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'ext.db'}",
        secret_key="test-extension-spi",
        enable_multi_tenant=False,
        enable_builtin_ui=False,
        enable_builtin_admins=False,
    )


# --- ExtensionRegistry invariants ---


def test_registry_rejects_duplicate_names():
    class A(AdminExtension):
        name = "dup"

    class B(AdminExtension):
        name = "dup"

    reg = ExtensionRegistry()
    reg.register(A())
    with pytest.raises(DuplicateExtensionError):
        reg.register(B())


def test_registry_rejects_extension_without_name():
    class Anon(AdminExtension):
        pass  # forgot to set name

    reg = ExtensionRegistry()
    with pytest.raises(ValueError, match="non-empty 'name'"):
        reg.register(Anon())


def test_registry_rejects_non_extension():
    reg = ExtensionRegistry()
    with pytest.raises(TypeError):
        reg.register(object())  # type: ignore[arg-type]


def test_registry_freeze_blocks_further_registration():
    class A(AdminExtension):
        name = "a"

    reg = ExtensionRegistry()
    reg.register(A())
    reg.freeze()
    with pytest.raises(RegistryFrozenError):
        reg.register(A())


def test_registry_preserves_order():
    class A(AdminExtension):
        name = "a"

    class B(AdminExtension):
        name = "b"

    class C(AdminExtension):
        name = "c"

    reg = ExtensionRegistry()
    reg.register_all([A(), B(), C()])
    assert reg.names() == ("a", "b", "c")


# --- create_admin lifecycle ---


def test_extension_hooks_called_in_documented_order(tmp_path):
    call_log: list[str] = []

    class TraceExt(AdminExtension):
        name = "trace"

        def configure(self, config):
            call_log.append("configure")

        def register_permissions(self, registry):
            call_log.append("register_permissions")

        def register_protected_fields(self, registry):
            call_log.append("register_protected_fields")

        def register_contract_contributions(self, registry):
            call_log.append("register_contract_contributions")

        def register_navigation(self, registry):
            call_log.append("register_navigation")

        def register_routes(self, app, ctx):
            call_log.append("register_routes")
            assert isinstance(ctx, ExtensionContext)

    create_admin(
        config=_config(tmp_path),
        register=lambda reg: reg.register(ThingAdmin),
        extensions=[TraceExt()],
    )

    assert call_log == [
        "configure",
        "register_permissions",
        "register_protected_fields",
        "register_contract_contributions",
        "register_navigation",
        "register_routes",
    ]


def test_extension_contributions_land_on_runtime(tmp_path):
    class ContribExt(AdminExtension):
        name = "contrib"

        def register_permissions(self, registry):
            registry.register("contrib.foo.list", "contrib.foo.create")

        def register_protected_fields(self, registry):
            registry.register("contrib_secret_token")

        def register_contract_contributions(self, registry):
            registry.add("contrib", {"hello": "world"})

        def register_navigation(self, registry):
            registry.add_item(
                id="contrib.list",
                label="Contrib List",
                path="/admin/contrib",
                permission="contrib.foo.list",
            )

    app = create_admin(
        config=_config(tmp_path),
        extensions=[ContribExt()],
    )
    runtime = app.state.adminfoundry

    assert "contrib.foo.list" in runtime.permission_registry.all()
    assert "contrib.foo.create" in runtime.permission_registry.all()
    assert "contrib_secret_token" in runtime.protected_fields
    assert runtime.contract_contributions.all() == {"contrib": {"hello": "world"}}
    nav = runtime.navigation.all()
    assert len(nav) == 1
    assert nav[0].id == "contrib.list"
    assert nav[0].permission == "contrib.foo.list"


def test_registries_are_frozen_after_create_admin(tmp_path):
    create_admin(config=_config(tmp_path))
    # Re-fetch the runtime via a freshly created app — Phase 5 freezes
    # every extension-side registry after setup.
    app = create_admin(config=_config(tmp_path))
    runtime = app.state.adminfoundry
    assert runtime.permission_registry.is_frozen
    assert runtime.contract_contributions.is_frozen
    assert runtime.navigation.is_frozen
    assert runtime.protected_fields.is_frozen
    assert runtime.extensions.is_frozen


def test_extension_routes_win_over_crud_dynamic_path(tmp_path):
    """An extension that mounts /{resource}/_export must be matched before
    the dynamic CRUD /{resource}/{id} route."""

    class RouteExt(AdminExtension):
        name = "route_test"

        def register_routes(self, app, ctx):
            sub = APIRouter()

            @sub.get("/{resource}/_probe")
            async def _probe(resource: str):
                return {"probed": resource}

            app.include_router(sub, prefix=ctx.config.admin_api_prefix)

    app = create_admin(
        config=_config(tmp_path),
        register=lambda reg: reg.register(ThingAdmin),
        extensions=[RouteExt()],
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/v1/admin/scaffold_things/_probe")
    assert resp.status_code == 200
    assert resp.json() == {"probed": "scaffold_things"}


def test_extensions_default_empty_tuple_is_noop(tmp_path):
    app = create_admin(config=_config(tmp_path))
    assert len(app.state.adminfoundry.extensions) == 0


def test_extension_configure_can_abort_startup(tmp_path):
    class BadConfigExt(AdminExtension):
        name = "bad_config"

        def configure(self, config):
            raise RuntimeError("bad config")

    with pytest.raises(RuntimeError, match="bad config"):
        create_admin(config=_config(tmp_path), extensions=[BadConfigExt()])


# --- async lifespan composition ---


def test_extension_startup_and_shutdown_called_around_user_lifespan(tmp_path):
    call_log: list[str] = []

    class LifeExt(AdminExtension):
        name = "life"

        async def startup(self, app):
            call_log.append("ext_startup")

        async def shutdown(self, app):
            call_log.append("ext_shutdown")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def user_lifespan(app):
        call_log.append("user_lifespan_enter")
        yield
        call_log.append("user_lifespan_exit")

    app = create_admin(
        config=_config(tmp_path),
        extensions=[LifeExt()],
        lifespan=user_lifespan,
    )

    with TestClient(app, raise_server_exceptions=False):
        pass

    assert call_log == [
        "ext_startup",
        "user_lifespan_enter",
        "user_lifespan_exit",
        "ext_shutdown",
    ]


def test_shutdown_in_reverse_registration_order(tmp_path):
    call_log: list[str] = []

    class _ExtFactory:
        def __init__(self, ident: str) -> None:
            self.ident = ident

        def make(self) -> AdminExtension:
            ident = self.ident

            class _Ext(AdminExtension):
                name = ident

                async def startup(self, app):
                    call_log.append(f"start:{ident}")

                async def shutdown(self, app):
                    call_log.append(f"stop:{ident}")

            return _Ext()

    app = create_admin(
        config=_config(tmp_path),
        extensions=[_ExtFactory("a").make(), _ExtFactory("b").make(), _ExtFactory("c").make()],
    )

    with TestClient(app, raise_server_exceptions=False):
        pass

    assert call_log == ["start:a", "start:b", "start:c", "stop:c", "stop:b", "stop:a"]


def test_shutdown_exceptions_are_swallowed(tmp_path):
    class BrokenShutdownExt(AdminExtension):
        name = "broken"

        async def shutdown(self, app):
            raise RuntimeError("shutdown failed")

    app = create_admin(config=_config(tmp_path), extensions=[BrokenShutdownExt()])

    # The TestClient context exit triggers lifespan shutdown. We expect
    # no exception to propagate — the warning is logged but swallowed.
    with TestClient(app, raise_server_exceptions=False):
        pass  # exits cleanly
