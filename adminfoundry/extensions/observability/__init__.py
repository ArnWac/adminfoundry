"""Observability extension — admin metrics dashboard widgets and (future) exporters.

Reads from the neutral core runtime counter store at `adminfoundry.runtime_metrics`.
The counter store itself lives in core so that core middleware and health endpoints
can write/read without depending on this extension being registered.

Optional: add ObservabilityExtension() to CoreAdminConfig.extensions to enable
the metrics dashboard widget. Future versions may contribute Prometheus/OTel
exporters here as well.
"""
from adminfoundry.extensions import ExtensionBase
from adminfoundry.extensions.observability.widgets import AdminMetricsWidget


class ObservabilityExtension(ExtensionBase):
    name = "observability"
    version = "0.1.0"
    is_optional = True

    def get_capabilities(self) -> dict:
        return {
            "request_counters": True,
            "action_counters": True,
            "audit_failure_tracking": True,
            "contract_version_usage": True,
            "client_type_tracking": True,
        }

    def get_dashboard_widgets(self) -> list:
        return [AdminMetricsWidget()]

    def startup_check(self) -> None:
        from adminfoundry.runtime_metrics import get_snapshot  # noqa: F401


__all__ = ["ObservabilityExtension", "AdminMetricsWidget"]
