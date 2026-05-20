"""Tenant resolution: slug extraction, in-memory caching, DB lookup."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import select
from starlette.requests import Request

from adminfoundry.models.tenant import Tenant
from adminfoundry.tenancy.context import TenantContext

_TENANT_TTL = 30  # seconds
_tenant_cache: dict[str, tuple] = {}


def clear_tenant_cache() -> None:
    _tenant_cache.clear()


def _mem_get(slug: str) -> tuple[bool, TenantContext | None]:
    entry = _tenant_cache.get(slug)
    if entry and time.monotonic() < entry[1]:
        return True, entry[0]
    return False, None


def _mem_set(slug: str, ctx: TenantContext | None) -> None:
    _tenant_cache[slug] = (ctx, time.monotonic() + _TENANT_TTL)


def _get_resolution_strategy(request: Request) -> tuple[str, str]:
    """Return (strategy, header_name) from runtime config or defaults."""
    runtime = getattr(getattr(request.app, "state", None), "adminfoundry", None)
    if runtime is not None:
        return (
            runtime.config.tenant_resolution or "header",
            runtime.config.tenant_header_name or "X-Tenant-Slug",
        )
    return "header", "X-Tenant-Slug"


def _extract_slug(request: Request) -> str | None:
    strategy, header_name = _get_resolution_strategy(request)
    if strategy == "subdomain":
        host = request.headers.get("host", "").split(":")[0]
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[0]
        return None
    return request.headers.get(header_name)


async def resolve_tenant(request: Request) -> TenantContext | None:
    """Resolve and return the TenantContext for the request, or None."""
    slug = _extract_slug(request)
    if not slug:
        return None

    hit, ctx = _mem_get(slug)
    if not hit:
        runtime = request.app.state.adminfoundry
        async with runtime.db.session() as session:
            result = await session.execute(select(Tenant).where(Tenant.slug == slug))
            tenant = result.scalar_one_or_none()
        ctx = TenantContext.from_orm(tenant) if tenant is not None else None
        _mem_set(slug, ctx)

    return ctx


async def resolve_impersonation_tenant(
    payload: dict, current_tenant: TenantContext | None, db
) -> TenantContext | None:
    """Return TenantContext for a same-origin impersonation token."""
    if current_tenant is not None:
        return current_tenant
    if not (payload.get("impersonated_by") and payload.get("tenant_id")):
        return None
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(payload["tenant_id"])))
    ).scalar_one_or_none()
    return TenantContext.from_orm(tenant) if tenant is not None else None
