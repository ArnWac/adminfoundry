"""FastAPI dependencies for tenant-scoped authorization."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adminfoundry.auth.dependencies import get_current_user
from adminfoundry.db.dependencies import get_async_session
from adminfoundry.models.tenant_membership import TenantMembership
from adminfoundry.models.tenant_rbac import TenantMembershipRole, TenantRole
from adminfoundry.models.user import User
from adminfoundry.tenancy.context import TenantAuthContext
from adminfoundry.tenancy.schema_strategy import set_search_path


async def require_tenant_membership(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> TenantMembership | None:
    """Enforce active tenant membership for every tenant-scoped request.

    - No tenant context (root panel): pass through, return None.
    - Superadmin + impersonation token: skip DB membership check, return None.
    - Any other user in tenant context: must have an active TenantMembership.
    """
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        return None

    payload = getattr(request.state, "token_payload", {})
    is_impersonating = bool(payload.get("impersonated_by"))
    if current_user.is_superadmin and is_impersonating:
        token_tenant_id = payload.get("tenant_id")
        if not token_tenant_id or str(token_tenant_id) != str(tenant.id):
            raise HTTPException(
                status_code=403,
                detail="Impersonation token is not valid for this tenant",
            )
        return None

    result = await db.execute(
        select(TenantMembership)
        .where(TenantMembership.user_id == current_user.id)
        .where(TenantMembership.tenant_id == tenant.id)
        .where(TenantMembership.is_active == True)  # noqa: E712
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(status_code=403, detail="You do not have access to this tenant")

    request.state.tenant_membership = membership
    return membership


async def require_tenant_auth_context(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> TenantAuthContext | None:
    """Build a TenantAuthContext by verifying public membership then loading
    tenant-local roles via SET LOCAL search_path on the shared session."""
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        return None

    payload = getattr(request.state, "token_payload", {})
    is_impersonating = bool(payload.get("impersonated_by"))
    if current_user.is_superadmin and is_impersonating:
        token_tenant_id = payload.get("tenant_id")
        if not token_tenant_id or str(token_tenant_id) != str(tenant.id):
            raise HTTPException(
                status_code=403,
                detail="Impersonation token is not valid for this tenant",
            )
        return None

    membership = (
        await db.execute(
            select(TenantMembership)
            .where(TenantMembership.user_id == current_user.id)
            .where(TenantMembership.tenant_id == tenant.id)
            .where(TenantMembership.is_active == True)  # noqa: E712
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="You do not have access to this tenant")

    roles: list[TenantRole] = []
    permission_keys: set[str] = set()

    database_url = request.app.state.adminfoundry.config.database_url
    if "postgresql" in database_url:
        await set_search_path(db, tenant.schema_name)
        role_rows = (
            (
                await db.execute(
                    select(TenantRole)
                    .join(TenantMembershipRole, TenantMembershipRole.role_id == TenantRole.id)
                    .where(TenantMembershipRole.membership_id == membership.id)
                    .options(selectinload(TenantRole.permissions))
                )
            )
            .scalars()
            .all()
        )
        roles = list(role_rows)
        for role in roles:
            for perm in role.permissions:
                permission_keys.add(perm.permission_key)

    ctx = TenantAuthContext(
        tenant=tenant,
        membership=membership,
        roles=roles,
        permission_keys=permission_keys,
    )
    request.state.tenant_auth = ctx
    request.state.tenant_membership = membership
    return ctx
