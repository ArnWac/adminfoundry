"""Smoke tests for the extension SPI itself.

Verifies the contract between :func:`adminfoundry.create_admin` and the
``extensions=`` parameter:

* extensions are invoked once with ``(registry, app, config)``,
* they run after the user's ``register`` callback,
* they run before core routes are mounted (so an extension router that
  uses a static path segment can outrank the dynamic CRUD path).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

from adminfoundry import CoreAdminConfig, ModelAdmin, create_admin
from adminfoundry.extensions import Extension


class _Base(DeclarativeBase):
    pass


class Thing(_Base):
    __tablename__ = "things"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)


class ThingAdmin(ModelAdmin):
    model = Thing


def _config(tmp_path) -> CoreAdminConfig:
    return CoreAdminConfig(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'ext.db'}",
        secret_key="test-extension-spi",
        enable_multi_tenant=False,
        enable_builtin_ui=False,
        enable_builtin_admins=False,
    )


def test_extension_invoked_with_three_args(tmp_path):
    captured: list[tuple] = []

    def ext(registry, app, config) -> None:
        captured.append((registry, app, config))

    create_admin(
        config=_config(tmp_path),
        register=lambda reg: reg.register(ThingAdmin),
        extensions=[ext],
    )
    assert len(captured) == 1
    registry, app, config = captured[0]
    assert registry.get("things") is not None
    assert app is not None
    assert config.secret_key == "test-extension-spi"


def test_extension_runs_after_user_register(tmp_path):
    order: list[str] = []

    def user_register(registry) -> None:
        order.append("user")
        registry.register(ThingAdmin)

    def ext(registry, app, config) -> None:
        # Extension can see what the user registered.
        order.append("ext")
        assert registry.get("things") is not None

    create_admin(config=_config(tmp_path), register=user_register, extensions=[ext])
    assert order == ["user", "ext"]


def test_extension_routes_win_over_crud_dynamic_path(tmp_path):
    """An extension that mounts /{resource}/_export must be matched before the
    dynamic CRUD /{resource}/{id} route."""

    def ext(registry, app, config) -> None:
        sub = APIRouter()

        @sub.get("/{resource}/_export")
        async def _export(resource: str):
            return {"export": resource}

        app.include_router(sub, prefix=config.admin_api_prefix)

    app = create_admin(
        config=_config(tmp_path),
        register=lambda reg: reg.register(ThingAdmin),
        extensions=[ext],
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/v1/admin/things/_export")
    assert resp.status_code == 200
    assert resp.json() == {"export": "things"}


def test_extensions_default_empty_tuple_is_noop(tmp_path):
    """Omitting ``extensions=`` must not change behaviour."""
    app = create_admin(
        config=_config(tmp_path),
        register=lambda reg: reg.register(ThingAdmin),
    )
    assert app is not None


def test_extension_type_alias_is_callable_typed():
    """Sanity: the :data:`Extension` alias is a Callable[..., None]."""
    assert callable(lambda r, a, c: None)
    # Mostly a docs-anchor — the type alias is checked by mypy/ruff, not pytest.
    _: Extension = lambda r, a, c: None  # noqa: E731
    assert _ is not None
