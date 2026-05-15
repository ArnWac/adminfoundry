"""Dashboard widget base types — V1 contract."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal


DashboardWidgetType = Literal["stats", "counts", "table", "chart", "status", "custom"]


@dataclass(frozen=True)
class DashboardWidgetContext:
    user: Any
    db: Any
    request: Any
    tenant: Any | None
    tenant_id: str | None
    is_superadmin: bool
    capabilities: frozenset[str] = field(default_factory=frozenset)


class DashboardWidget:
    """Base class for dashboard widgets.

    Subclass and override ``get_data`` (required) and ``is_visible`` (optional).
    """

    id: str = ""
    title: str = ""
    type: DashboardWidgetType = "stats"
    superadmin_only: bool = False
    required_capabilities: frozenset[str] = frozenset()

    async def is_visible(self, ctx: DashboardWidgetContext) -> bool:
        if self.superadmin_only and not ctx.is_superadmin:
            return False
        if self.required_capabilities and not self.required_capabilities.issubset(ctx.capabilities):
            return False
        return True

    async def get_data(self, ctx: DashboardWidgetContext) -> dict[str, Any]:
        return {}
