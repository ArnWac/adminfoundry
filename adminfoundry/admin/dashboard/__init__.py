from adminfoundry.admin.dashboard.widget import (
    DashboardWidget,
    DashboardWidgetContext,
    DashboardWidgetType,
)
from adminfoundry.admin.dashboard.builtins import ModelCountsWidget, DEFAULT_WIDGETS
from adminfoundry.admin.dashboard.registry import DashboardRegistry, dashboard_registry
from adminfoundry.admin.dashboard.responses import DashboardResponse, DashboardWidgetResponse

__all__ = [
    "DashboardWidget",
    "DashboardWidgetContext",
    "DashboardWidgetType",
    "ModelCountsWidget",
    "DEFAULT_WIDGETS",
    "DashboardRegistry",
    "dashboard_registry",
    "DashboardResponse",
    "DashboardWidgetResponse",
]
