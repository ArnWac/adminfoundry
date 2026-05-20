from adminfoundry.core.app_factory import create_admin
from adminfoundry.core.config import CoreAdminConfig
from adminfoundry.registry import AdminRegistry, ModelAdmin

__version__ = "0.1.0"

__all__ = [
    "AdminRegistry",
    "CoreAdminConfig",
    "ModelAdmin",
    "__version__",
    "create_admin",
]
