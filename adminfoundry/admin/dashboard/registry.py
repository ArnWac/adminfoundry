"""Dashboard widget registry — collects core, extension, and app widgets."""
from __future__ import annotations

from adminfoundry.admin.dashboard.widget import DashboardWidget
from adminfoundry.admin.dashboard.builtins import DEFAULT_WIDGETS


class DashboardRegistry:
    def __init__(self) -> None:
        self._widgets: list[DashboardWidget] = []

    def reset(self, base: list[DashboardWidget] | None = None) -> None:
        """Re-initialize with the given base list or core defaults."""
        self._widgets = list(base if base is not None else DEFAULT_WIDGETS)

    def register(self, widget: DashboardWidget) -> None:
        self._widgets.append(widget)

    def all(self) -> list[DashboardWidget]:
        return list(self._widgets)


dashboard_registry = DashboardRegistry()
