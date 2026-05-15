"""Webhook extension — HTTP delivery of admin signal events.

Enable by adding WebhookExtension() to CoreAdminConfig.extensions::

    from adminfoundry.extensions.webhooks import WebhookExtension
    app = create_admin(config=CoreAdminConfig(extensions=[WebhookExtension()]))

Subscriptions can be managed via the admin UI (/api/v1/admin/webhook-subscriptions)
or registered imperatively at startup::

    from adminfoundry.extensions.webhooks import register
    register(
        url="https://my-service.com/hooks",
        events=["post_create", "post_delete"],
        secret="hmac-secret",
    )

Payload shape::

    {
        "event":      "post_create",
        "timestamp":  1718000000,
        "model_name": "articles",
        "object_id":  "uuid",
        "actor":      "admin@example.com",
        "changes":    {...} or null
    }
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Callable

from adminfoundry.extensions import ExtensionBase


# ---------------------------------------------------------------------------
# In-process dispatcher (imperative API — used alongside DB subscriptions)
# ---------------------------------------------------------------------------

class _WebhookTarget:
    __slots__ = ("url", "events", "secret", "model_filter")

    def __init__(
        self,
        url: str,
        events: list[str],
        secret: str | None,
        model_filter: list[str] | None,
    ) -> None:
        self.url = url
        self.events = set(events)
        self.secret = secret
        self.model_filter = set(model_filter) if model_filter else None

    def matches(self, event: str, model_name: str | None) -> bool:
        if event not in self.events:
            return False
        if self.model_filter is not None and model_name not in self.model_filter:
            return False
        return True


_targets: list[_WebhookTarget] = []


def register(
    url: str,
    events: list[str],
    secret: str | None = None,
    model_filter: list[str] | None = None,
) -> None:
    """Register an HTTP endpoint to receive admin signal events."""
    from adminfoundry import signals as _signals

    target = _WebhookTarget(url, events, secret, model_filter)
    _targets.append(target)

    def _make_handler(event_name: str) -> Callable:
        async def _handler(**kwargs: Any) -> None:
            if not target.matches(event_name, kwargs.get("model_name")):
                return
            await _post(target, _build_payload(event_name, kwargs))
        return _handler

    for event in events:
        _signals.connect(event, _make_handler(event))


def clear() -> None:
    """Deregister all in-process webhooks — useful in tests."""
    _targets.clear()


def _build_payload(event: str, kwargs: Any) -> dict:
    obj = kwargs.get("obj")
    user = kwargs.get("user")
    return {
        "event": event,
        "timestamp": int(time.time()),
        "model_name": kwargs.get("model_name"),
        "object_id": str(getattr(obj, "id", None) or kwargs.get("object_id") or ""),
        "actor": getattr(user, "email", None),
        "changes": kwargs.get("changes"),
    }


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def _post(target: _WebhookTarget, payload: dict) -> None:
    try:
        import httpx
    except ImportError:
        raise RuntimeError("adminfoundry webhooks require httpx: pip install httpx")
    body = json.dumps(payload, default=str).encode()
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-adminfoundry-Event": payload["event"],
    }
    if target.secret:
        headers["X-Signature-256"] = _sign(body, target.secret)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(target.url, content=body, headers=headers)
    except Exception:
        pass  # webhook delivery failures must never affect the main request path


# ---------------------------------------------------------------------------
# ExtensionBase implementation
# ---------------------------------------------------------------------------

class WebhookExtension(ExtensionBase):
    """Webhook delivery extension.

    Registers WebhookSubscription and WebhookDelivery models, exposes admin
    CRUD routes for managing subscriptions, and provides the in-process
    dispatcher as a fallback delivery path.
    """

    name = "webhooks"
    version = "0.1.0"
    is_optional = True

    def get_models(self) -> list:
        from adminfoundry.extensions.webhooks.models import WebhookDelivery, WebhookSubscription
        return [WebhookSubscription, WebhookDelivery]

    def get_admin_registrations(self) -> list:
        from adminfoundry.admin.model_admin import ModelAdmin
        from adminfoundry.extensions.webhooks.models import WebhookSubscription

        class WebhookSubscriptionAdmin(ModelAdmin):
            model = WebhookSubscription
            list_display = ["url", "events", "is_active", "created_at"]
            readonly_fields = ["id", "created_at", "updated_at"]
            search_fields = ["url"]
            filter_fields = ["is_active"]

        return [WebhookSubscriptionAdmin()]

    def get_capabilities(self) -> dict:
        return {
            "http_delivery": True,
            "hmac_signing": True,
            "model_filter": True,
        }

    def health_check(self) -> dict:
        return {
            "status": "ok",
            "extension": self.name,
            "version": self.version,
            "registered_targets": len(_targets),
        }


__all__ = ["WebhookExtension", "register", "clear"]
