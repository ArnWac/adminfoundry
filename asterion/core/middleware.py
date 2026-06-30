"""Operational middlewares: request IDs, access logs, safe response headers.

``RequestIDMiddleware``
    Accepts an inbound ``X-Request-ID`` header, generates a UUID4 if
    absent, exposes it via ``request.state.request_id``, and echoes it
    back as a response header. Anything that wants to correlate a log
    line, an audit row, or an error response with the original request
    reads ``request.state.request_id``.

``AccessLogMiddleware``
    Emits one ``logger.info("request", extra={...})`` per request with
    request_id, method, path, status_code, duration_ms, plus tenant_id
    and actor_user_id when those have been populated on ``request.state``
    by ``TenantMiddleware`` / ``get_current_user``.

``SecurityHeadersMiddleware``
    Adds the three baseline security headers the production-ready prompt
    requires (``X-Content-Type-Options``, ``Referrer-Policy``,
    ``X-Frame-Options``). A ``Content-Security-Policy`` is emitted only when
    ``CoreAdminConfig.content_security_policy`` is set (Review R14): the
    bundled UI uses inline config scripts that a strict ``script-src 'self'``
    would block, so the default is header-less, but API-first deployments with
    their own frontend can opt into a strict policy.

    **CSP nonce (G10).** If the configured policy contains the literal token
    ``{nonce}`` (:data:`CSP_NONCE_PLACEHOLDER`), the middleware mints a fresh
    per-request nonce, substitutes it into the header, and publishes it on
    ``request.state.csp_nonce`` so the bundled UI's templates can stamp their
    inline ``<script>`` blocks with a matching ``nonce=…``. That lets a strict
    ``script-src 'self' 'nonce-{nonce}'`` cover the bundled UI's own inline
    config while still blocking any injected inline script — closing the XSS gap
    without dropping to ``'unsafe-inline'``.
"""

from __future__ import annotations

import logging
import secrets
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"

#: Literal token an operator places in ``content_security_policy`` (e.g.
#: ``script-src 'self' 'nonce-{nonce}'``) to opt into per-request nonces.
CSP_NONCE_PLACEHOLDER = "{nonce}"

access_logger = logging.getLogger("asterion.access")


def _generate_request_id() -> str:
    return uuid.uuid4().hex


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming or _generate_request_id()
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Structured per-request log line (plan §PR-4 / roadmap §E5 core part).

    Logged at INFO via ``asterion.access``. The :class:`JSONFormatter`
    from :mod:`asterion.core.logging` picks up every contextual field
    we set on ``extra``.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            access_logger.exception(
                "request",
                extra=_log_extra(request, status_code=500, duration_ms=duration_ms),
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        access_logger.info(
            "request",
            extra=_log_extra(request, status_code=response.status_code, duration_ms=duration_ms),
        )
        return response


def _log_extra(request: Request, *, status_code: int, duration_ms: float) -> dict:
    extra: dict[str, object] = {
        "request_id": getattr(request.state, "request_id", None),
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }
    # Reading SQLAlchemy-bound attributes after the request session has
    # closed can trigger DetachedInstanceError. We catch everything so a
    # logging failure can never turn a successful request into a 500.
    try:
        actor = getattr(request.state, "current_user", None)
        if actor is not None:
            actor_id = getattr(actor, "id", None)
            if actor_id is not None:
                extra["actor_user_id"] = str(actor_id)
    except Exception:
        pass
    try:
        tenant = getattr(request.state, "tenant", None)
        if tenant is not None:
            tenant_id = getattr(tenant, "id", None)
            if tenant_id is not None:
                extra["tenant_id"] = str(tenant_id)
    except Exception:
        pass
    return extra


_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, csp: str | None = None) -> None:
        super().__init__(app)
        self._csp = csp
        #: True when the policy opts into per-request nonces (G10).
        self._uses_nonce = csp is not None and CSP_NONCE_PLACEHOLDER in csp

    async def dispatch(self, request: Request, call_next):
        # Mint the nonce BEFORE the handler runs so templates rendered inside
        # call_next can read request.state.csp_nonce and stamp their inline
        # scripts with it. 16 random bytes, base64url — well above the CSP
        # 128-bit recommendation.
        nonce: str | None = None
        if self._uses_nonce:
            nonce = secrets.token_urlsafe(16)
            request.state.csp_nonce = nonce

        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        # Review R14: emit a CSP only when configured. The bundled UI needs the
        # nonce path (G10) to survive a strict ``script-src``; without ``{nonce}``
        # the policy is sent verbatim (API-first deployments with their own UI).
        if self._csp:
            policy = self._csp.replace(CSP_NONCE_PLACEHOLDER, nonce) if nonce else self._csp
            response.headers.setdefault("Content-Security-Policy", policy)
        return response
