from __future__ import annotations

from collections.abc import Callable, Collection
from typing import Protocol

from fastapi import Depends

from adminfoundry.authz.permissions import assert_permission
from adminfoundry.tenancy.context import TenantAuthContext
from adminfoundry.tenancy.dependencies import require_tenant_auth_context


class PermissionContext(Protocol):
    permission_keys: Collection[str]


def require_permission_key(
    context: PermissionContext,
    required_permission: str,
) -> PermissionContext:
    assert_permission(context.permission_keys, required_permission)
    return context


def require_permission(
    required_permission: str,
) -> Callable[..., TenantAuthContext]:
    async def dependency(
        context: TenantAuthContext = Depends(require_tenant_auth_context),
    ) -> TenantAuthContext:
        require_permission_key(context, required_permission)
        return context

    return dependency
