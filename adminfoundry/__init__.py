"""adminfoundry — FastAPI admin framework with built-in UI, auth, and multi-tenancy.

V1 public API is intentionally minimal. Use explicit submodule imports for
dashboards, actions, signals, cache, storage, and i18n:

    from adminfoundry.admin.dashboard import DashboardWidget
    from adminfoundry.actions import BulkDeleteAction
    from adminfoundry.cache import cache
    from adminfoundry.storage import storage
    from adminfoundry.i18n import t
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
