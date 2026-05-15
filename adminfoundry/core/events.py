"""Tiny in-process event bus for cross-cutting telemetry events.

Distinct from `adminfoundry.signals` (model-level signals). EventBus carries
generic operational events (request_finished, audit_write_failed, etc.) that
optional extensions like observability can subscribe to.

A fresh `EventBus()` is attached to each app's runtime — no module-level
singleton, no cross-app handler leakage.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

_log = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = {}

    def subscribe(self, event: str, handler: Handler) -> None:
        self._handlers.setdefault(event, []).append(handler)

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        for handler in self._handlers.get(event, ()):
            try:
                await handler(payload)
            except Exception:
                _log.exception("EventBus handler for %r failed", event)
