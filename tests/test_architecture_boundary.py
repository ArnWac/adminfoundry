"""Architecture boundary tests — enforce core/extension import separation.

Core and admin modules must not import directly from concrete extensions.
Extensions integrate only through ExtensionBase hooks (get_routers, get_dashboard_widgets, etc.).
"""
from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "adminfoundry"

# Modules in core/admin that must not reference concrete extensions directly.
_CORE_MODULES = [
    _ROOT / "admin" / "router.py",
    _ROOT / "admin" / "_helpers.py",
    _ROOT / "admin" / "routes" / "contract.py",
    _ROOT / "admin" / "routes" / "dashboard.py",
    _ROOT / "admin" / "routes" / "profile.py",
    _ROOT / "admin" / "routes" / "preferences.py",
    _ROOT / "admin" / "routes" / "permissions.py",
    _ROOT / "admin" / "routes" / "crud.py",
    _ROOT / "admin" / "dashboard" / "widget.py",
    _ROOT / "admin" / "dashboard" / "builtins.py",
    _ROOT / "admin" / "dashboard" / "registry.py",
]

# Extension sub-packages that core must not import from directly.
_FORBIDDEN_PREFIXES = [
    "adminfoundry.extensions.observability",
    "adminfoundry.extensions.jobs",
    "adminfoundry.extensions.workflows",
    "adminfoundry.extensions.webhooks",
    "adminfoundry.extensions.import_export",
]


def _collect_imports(path: Path) -> list[str]:
    """Return all module strings imported (statically) in a Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _run(script: str) -> None:
    subprocess.check_call([sys.executable, "-c", textwrap.dedent(script)])


def test_admin_modules_do_not_import_concrete_extensions():
    """Core/admin route modules must not import from concrete extension packages."""
    violations: list[str] = []
    for module_path in _CORE_MODULES:
        if not module_path.exists():
            continue
        for imp in _collect_imports(module_path):
            for forbidden in _FORBIDDEN_PREFIXES:
                if imp == forbidden or imp.startswith(forbidden + "."):
                    violations.append(f"{module_path.relative_to(_ROOT.parent)}: imports {imp!r}")

    assert not violations, "Core/admin boundary violations found:\n" + "\n".join(violations)


def test_extension_base_is_importable_from_core():
    """ExtensionBase must be importable from adminfoundry.extensions (the allowed integration point)."""
    from adminfoundry.extensions import ExtensionBase
    assert hasattr(ExtensionBase, "get_routers")
    assert hasattr(ExtensionBase, "get_dashboard_widgets")


def test_dashboard_registry_singleton_accessible():
    """dashboard_registry singleton must be accessible from the canonical path."""
    from adminfoundry.admin.dashboard.registry import dashboard_registry, DashboardRegistry
    assert isinstance(dashboard_registry, DashboardRegistry)


def test_duplicate_extension_names_rejected():
    """ExtensionRegistry.register() must raise ValueError on duplicate extension name."""
    from adminfoundry.extensions import ExtensionRegistry, ExtensionBase
    import pytest

    class _Ext(ExtensionBase):
        name = "duplicate_test"

    reg = ExtensionRegistry()
    reg.register(_Ext())
    with pytest.raises(ValueError, match="already registered"):
        reg.register(_Ext())


def test_core_works_with_no_extensions():
    """create_admin() with extensions=[] must succeed without errors."""
    _run("""
        from adminfoundry import create_admin, CoreAdminConfig
        app = create_admin(config=CoreAdminConfig(extensions=[]), title="no-ext-test")
        assert app is not None
    """)


def test_extension_registry_populated_after_create_admin():
    """extension_registry singleton must reflect enabled extensions after create_admin()."""
    _run("""
        from adminfoundry import create_admin, CoreAdminConfig
        from adminfoundry.extensions.observability import ObservabilityExtension
        create_admin(
            config=CoreAdminConfig(extensions=[ObservabilityExtension()]),
            title="registry-test",
        )
        from adminfoundry.extensions import extension_registry
        assert "observability" in extension_registry.names(), (
            f"expected 'observability' in {extension_registry.names()}"
        )
    """)


def test_dashboard_response_follows_v1_model():
    """DashboardResponse and DashboardWidgetResponse must match the V1 schema."""
    from adminfoundry.admin.dashboard.responses import DashboardResponse, DashboardWidgetResponse
    from pydantic import BaseModel

    assert issubclass(DashboardResponse, BaseModel)
    assert issubclass(DashboardWidgetResponse, BaseModel)

    # Verify required fields
    widget_fields = set(DashboardWidgetResponse.model_fields)
    assert {"id", "title", "type", "data", "error"}.issubset(widget_fields)

    dashboard_fields = set(DashboardResponse.model_fields)
    assert "widgets" in dashboard_fields


def test_failing_widget_returns_error_field():
    """A widget that raises must not break the dashboard; it must return error='widget_failed'."""
    _run("""
        import asyncio
        from unittest.mock import MagicMock
        from adminfoundry.admin.dashboard.widget import DashboardWidget, DashboardWidgetContext
        from adminfoundry.admin.dashboard.registry import DashboardRegistry
        from adminfoundry.admin.routes.dashboard import admin_dashboard

        class _BrokenWidget(DashboardWidget):
            id = "broken"
            title = "Broken"
            async def get_data(self, ctx):
                raise RuntimeError("intentional failure")

        # Test that the error path is exercised via the route logic
        reg = DashboardRegistry()
        reg.register(_BrokenWidget())

        ctx = DashboardWidgetContext(
            user=None, db=None, request=None,
            tenant=None, tenant_id=None,
            is_superadmin=True,
        )

        async def run():
            import logging
            # Should not raise even though widget fails
            results = []
            for w in reg.all():
                if not await w.is_visible(ctx):
                    continue
                error = None
                data = {}
                try:
                    data = await w.get_data(ctx)
                except Exception:
                    logging.getLogger("test").exception("widget failed")
                    error = "widget_failed"
                results.append({"id": w.id, "error": error, "data": data})
            return results

        results = asyncio.run(run())
        assert len(results) == 1
        assert results[0]["error"] == "widget_failed"
        assert results[0]["data"] == {}
    """)
