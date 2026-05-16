"""adminfoundry — FastAPI admin framework with built-in UI, auth, and multi-tenancy.

V1 public API is intentionally minimal. Use explicit submodule imports for
dashboards, actions, signals, and i18n:

    from adminfoundry.admin.dashboard import DashboardWidget
    from adminfoundry.actions import BulkDeleteAction
    from adminfoundry.i18n import t

Cache and storage are per-app: access via ``request.app.state.adminfoundry.cache``
and ``request.app.state.adminfoundry.storage``.
"""

from adminfoundry.admin.model_admin import ModelAdmin
from adminfoundry.admin.registry import admin_site
from adminfoundry.auth_provider import AuthProvider
from adminfoundry.core.app_factory import create_admin
from adminfoundry.core.config import CoreAdminConfig

__version__ = "0.1.0"

__all__ = [
    "create_admin",
    "CoreAdminConfig",
    "ModelAdmin",
    "admin_site",
    "AuthProvider",
    "__version__",
]
