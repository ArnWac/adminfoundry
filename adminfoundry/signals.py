"""Lightweight async event/signal system.

Usage::

    from adminfoundry.signals import on, emit

    @on("post_create")
    async def notify(model_name, obj, user, **_):
        print(f"{user.email} created {model_name}#{obj.id}")

    # Or connect imperatively:
    signals.connect("post_delete", my_handler)

Available events (fired by the admin router):
    post_create(model_name, obj, user)
    post_update(model_name, obj, user, changes)
    pre_delete(model_name, obj, user)
    post_delete(model_name, object_id, user)
    post_login(user)
    post_logout(user)
    post_password_change(user)
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable

_handlers: dict[str, list[Callable]] = defaultdict(list)


def connect(event: str, handler: Callable) -> None:
    """Register *handler* to be called when *event* is emitted."""
    _handlers[event].append(handler)


def disconnect(event: str, handler: Callable) -> None:
    """Remove *handler* from *event* (no-op if not registered)."""
    _handlers[event] = [h for h in _handlers[event] if h is not handler]


def on(event: str) -> Callable:
    """Decorator — register the decorated function as a handler for *event*."""
    def decorator(fn: Callable) -> Callable:
        connect(event, fn)
        return fn
    return decorator


async def emit(event: str, **kwargs: Any) -> None:
    """Fire all handlers registered for *event*, awaiting async ones."""
    for handler in list(_handlers.get(event, [])):
        try:
            result = handler(**kwargs)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass  # signal errors must never break the main request path


def clear(event: str | None = None) -> None:
    """Remove all handlers — useful in tests."""
    if event:
        _handlers.pop(event, None)
    else:
        _handlers.clear()
