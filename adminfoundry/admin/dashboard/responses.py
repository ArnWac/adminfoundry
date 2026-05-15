"""Typed dashboard API response models."""
from __future__ import annotations
from typing import Any

from pydantic import BaseModel

from adminfoundry.admin.dashboard.widget import DashboardWidgetType


class DashboardWidgetResponse(BaseModel):
    id: str
    title: str
    type: DashboardWidgetType
    data: dict[str, Any]
    error: str | None = None
    refresh_interval_seconds: int | None = None


class DashboardResponse(BaseModel):
    widgets: list[DashboardWidgetResponse]
