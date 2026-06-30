"""Per-tenant request rate limiting (roadmap G19, noisy-neighbour protection).

A single tenant hammering the API must not degrade service for the others. This
middleware counts each *tenant-scoped* request (one carrying a resolved tenant
slug) against a per-tenant sliding-window budget and returns ``429`` over budget.

Keying is by **tenant only** (``tenant:<slug>``), so one tenant's traffic can
never consume another's budget — the essential fairness guarantee. Requests
without a tenant (health, root, login) are not limited here; they have their own
controls (the login limiter, etc.).

The limiter reuses the existing
:class:`asterion.auth.rate_limiter.RateLimiterBackend` sliding-window counter:
``is_limited`` is checked first (block when already at the cap), otherwise the
hit is recorded — so exactly ``max`` requests pass per window and the next is
rejected. The in-process default is per-worker; swap ``runtime.tenant_rate_limiter``
for a shared backend (the ``rate_limit_redis`` extension) for multi-worker.

Everything is read from the runtime at request time, so the middleware is inert
(one attribute read + flag check, then pass-through) unless
``tenant_rate_limit_enabled`` is set — and it does not depend on middleware
ordering: the tenant slug is extracted directly from the request the same way
the resolver does.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from asterion.core.errors import RATE_LIMITED, error_response
from asterion.tenancy.resolver import _extract_slug


class TenantRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        runtime = getattr(getattr(request.app, "state", None), "asterion", None)
        if runtime is None or not getattr(runtime.config, "tenant_rate_limit_enabled", False):
            return await call_next(request)

        backend = getattr(runtime, "tenant_rate_limiter", None)
        if backend is None:
            return await call_next(request)

        slug = _extract_slug(request)
        if not slug:
            # Not a tenant-scoped request → not subject to the per-tenant budget.
            return await call_next(request)

        key = f"tenant:{slug}"
        if await backend.is_limited(key):
            return error_response(
                request,
                status_code=429,
                code=RATE_LIMITED,
                message="Per-tenant rate limit exceeded. Please retry later.",
            )
        await backend.record_failure(key)
        return await call_next(request)
