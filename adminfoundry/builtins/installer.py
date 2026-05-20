from __future__ import annotations

from adminfoundry.builtins.admin import BUILTIN_TENANT_ADMINS
from adminfoundry.registry import AdminRegistry, ModelAdmin


def install_builtin_admins(
    registry: AdminRegistry,
    *,
    include_tenant_admins: bool = True,
    extra_admins: tuple[type[ModelAdmin], ...] = (),
) -> None:
    if include_tenant_admins:
        for admin_class in BUILTIN_TENANT_ADMINS:
            if not registry.is_registered(admin_class.model):
                registry.register(admin_class)

    for admin_class in extra_admins:
        if not registry.is_registered(admin_class.model):
            registry.register(admin_class)


__all__ = [
    "install_builtin_admins",
]
