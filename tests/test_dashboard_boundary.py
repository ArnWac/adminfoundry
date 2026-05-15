"""Guard the Dashboard / Observability boundary.

Core dashboard provides infrastructure + generic widgets only.
Concrete metric widgets are contributed by ObservabilityExtension via
ExtensionBase.get_dashboard_widgets(). Disabled extensions contribute nothing.

Live-app tests run in a fresh subprocess to avoid mutating the module-level
extension_registry and dashboard_registry singletons.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap

from adminfoundry.admin.dashboard import (
    DEFAULT_WIDGETS,
    DashboardWidget,
    DashboardWidgetContext,
    DashboardWidgetType,
    DashboardResponse,
    DashboardWidgetResponse,
    ModelCountsWidget,
)


def _run(script: str) -> None:
    subprocess.check_call([sys.executable, "-c", textwrap.dedent(script)])


# ---------------------------------------------------------------------------
# Static / in-process checks
# ---------------------------------------------------------------------------

def test_default_widgets_contains_only_core_widgets():
    """DEFAULT_WIDGETS is the core generic widget list — ModelCountsWidget only."""
    assert len(DEFAULT_WIDGETS) == 1
    assert isinstance(DEFAULT_WIDGETS[0], ModelCountsWidget)


def test_dashboard_widget_context_is_dataclass():
    """DashboardWidgetContext must be a frozen dataclass with the V1 fields."""
    import dataclasses
    assert dataclasses.is_dataclass(DashboardWidgetContext)
    fields = {f.name for f in dataclasses.fields(DashboardWidgetContext)}
    assert fields >= {"user", "db", "request", "tenant", "tenant_id", "is_superadmin", "capabilities"}


def test_dashboard_widget_type_is_a_class_attribute():
    """DashboardWidget.type must be a class attribute, not a method."""
    w = ModelCountsWidget()
    assert isinstance(w.type, str)
    assert w.type == "counts"
    assert not callable(w.type)


def test_dashboard_widget_get_data_takes_context():
    """DashboardWidget.get_data must accept a DashboardWidgetContext, not loose args."""
    import inspect
    sig = inspect.signature(DashboardWidget.get_data)
    params = list(sig.parameters.keys())
    assert params == ["self", "ctx"], f"Unexpected signature params: {params}"


def test_dashboard_widget_has_is_visible():
    """DashboardWidget.is_visible must be an async method."""
    import inspect
    assert inspect.iscoroutinefunction(DashboardWidget.is_visible)


def test_dashboard_response_models_exist():
    """DashboardResponse and DashboardWidgetResponse must be importable Pydantic models."""
    from pydantic import BaseModel
    assert issubclass(DashboardResponse, BaseModel)
    assert issubclass(DashboardWidgetResponse, BaseModel)
    assert "error" in DashboardWidgetResponse.model_fields


def test_observability_extension_contributes_admin_metrics_widget():
    """ObservabilityExtension contributes AdminMetricsWidget via get_dashboard_widgets()."""
    from adminfoundry.extensions.observability import (
        ObservabilityExtension,
        AdminMetricsWidget,
    )

    widgets = ObservabilityExtension().get_dashboard_widgets()
    assert any(isinstance(w, AdminMetricsWidget) for w in widgets)
    assert all(isinstance(w, DashboardWidget) for w in widgets)


def test_observability_metrics_importable():
    """The observability counter store must be importable from the extension namespace."""
    from adminfoundry.extensions.observability.admin_metrics import get_snapshot
    snap = get_snapshot()
    assert "request_count" in snap
    assert "audit_write_failures" in snap


def test_runtime_metrics_core_module_does_not_exist():
    """runtime_metrics must not exist as a core module — metrics belong to observability."""
    import importlib
    import pytest as _pytest

    with _pytest.raises(ImportError):
        importlib.import_module("adminfoundry.runtime_metrics")


def test_old_middleware_tenant_shim_is_removed():
    """No shim: adminfoundry.middleware.tenant must not exist as a re-export."""
    import importlib
    import pytest as _pytest

    with _pytest.raises(ImportError):
        importlib.import_module("adminfoundry.middleware.tenant")


# ---------------------------------------------------------------------------
# Subprocess-isolated live-app checks
# ---------------------------------------------------------------------------

def test_observability_widgets_absent_when_extension_disabled():
    """With extensions=[], no widget with id=='admin_metrics' is in the registry."""
    _run("""
        from adminfoundry import create_admin, CoreAdminConfig
        create_admin(config=CoreAdminConfig(extensions=[]), title="boundary-test")
        from adminfoundry.admin.dashboard.registry import dashboard_registry
        ids = [w.id for w in dashboard_registry.all()]
        assert 'admin_metrics' not in ids, f"unexpected widget ids: {ids}"
    """)


def test_observability_widgets_present_when_extension_enabled():
    """With ObservabilityExtension() registered, admin_metrics widget is in the registry."""
    _run("""
        from adminfoundry import create_admin, CoreAdminConfig
        from adminfoundry.extensions.observability import ObservabilityExtension
        create_admin(
            config=CoreAdminConfig(extensions=[ObservabilityExtension()]),
            title="boundary-test",
        )
        from adminfoundry.admin.dashboard.registry import dashboard_registry
        ids = [w.id for w in dashboard_registry.all()]
        assert 'admin_metrics' in ids, f"missing admin_metrics in: {ids}"
    """)


def test_user_dashboard_widgets_appended_to_defaults():
    """User widgets in CoreAdminConfig.dashboard_widgets are appended to DEFAULT_WIDGETS."""
    _run("""
        from adminfoundry import create_admin, CoreAdminConfig
        from adminfoundry.admin.dashboard import DashboardWidget

        class _MyWidget(DashboardWidget):
            id = "my_widget"
            title = "Custom"

        widget = _MyWidget()
        create_admin(
            config=CoreAdminConfig(dashboard_widgets=[widget], extensions=[]),
            title="boundary-test",
        )
        from adminfoundry.admin.dashboard.registry import dashboard_registry
        ids = [w.id for w in dashboard_registry.all()]
        assert 'model_counts' in ids, f"core widget missing: {ids}"
        assert 'my_widget' in ids, f"custom widget missing: {ids}"
        assert ids.index('model_counts') < ids.index('my_widget'), "core widget must come first"
    """)


def test_user_dashboard_widgets_replace_when_mode_replace():
    """dashboard_widgets_mode='replace' fully replaces DEFAULT_WIDGETS."""
    _run("""
        from adminfoundry import create_admin, CoreAdminConfig
        from adminfoundry.admin.dashboard import DashboardWidget

        class _MyWidget(DashboardWidget):
            id = "my_widget"
            title = "Custom"

        widget = _MyWidget()
        create_admin(
            config=CoreAdminConfig(
                dashboard_widgets=[widget],
                dashboard_widgets_mode="replace",
                extensions=[],
            ),
            title="boundary-test",
        )
        from adminfoundry.admin.dashboard.registry import dashboard_registry
        ids = [w.id for w in dashboard_registry.all()]
        assert 'model_counts' not in ids, f"core widget should be replaced: {ids}"
        assert 'my_widget' in ids, f"custom widget missing: {ids}"
    """)
