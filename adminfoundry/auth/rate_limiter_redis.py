"""Redis-backed login rate limiter (Review R7).

A distributed, multi-worker-safe implementation of the
:class:`~adminfoundry.auth.rate_limiter.RateLimiterBackend` Protocol. Unlike
the in-memory default, the failure counters live in Redis, so every uvicorn
worker / process / instance shares one view and a restart does not reset the
window.

Core does **not** depend on ``redis``: this module is duck-typed against any
async Redis client (``redis.asyncio.Redis``, ``fakeredis.aioredis.FakeRedis``,
…). Install the client yourself — the ``rate-limit-redis`` extra pulls in
``redis``:

    pip install adminfoundry[rate-limit-redis]

then wire it in::

    import redis.asyncio as aioredis
    from adminfoundry import create_admin
    from adminfoundry.auth.rate_limiter_redis import RedisLoginRateLimiter

    app = create_admin(
        config=...,
        login_rate_limiter=RedisLoginRateLimiter(aioredis.from_url("redis://localhost:6379")),
    )

The window is a sliding one, modelled as a Redis sorted set per key whose
members are scored by their unix timestamp. ``record_failure`` appends an entry
and refreshes the key TTL; ``is_limited`` counts entries inside the window with
``ZCOUNT`` (read-only). The login flow keys on the lowercased email; a future
change can key on ``(email, ip)`` without touching this class — the key is
opaque here.
"""

from __future__ import annotations

import time
import uuid
from typing import Any


class RedisLoginRateLimiter:
    """Sliding-window login limiter backed by Redis sorted sets.

    Implements :class:`adminfoundry.auth.rate_limiter.RateLimiterBackend`.
    """

    def __init__(
        self,
        client: Any,
        *,
        max_failures: int = 5,
        window_seconds: int = 15 * 60,
        namespace: str = "adminfoundry:login-fail:",
    ) -> None:
        self._redis = client
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._namespace = namespace

    def _key(self, key: str) -> str:
        return f"{self._namespace}{key}"

    async def is_limited(self, key: str) -> bool:
        rkey = self._key(key)
        now = time.time()
        # Read-only count of failures still inside the window.
        count = await self._redis.zcount(rkey, now - self.window_seconds, "+inf")
        return int(count) >= self.max_failures

    async def record_failure(self, key: str) -> None:
        rkey = self._key(key)
        now = time.time()
        # Drop entries that have aged out, then append this failure. A random
        # suffix keeps the member unique even for two failures in the same
        # clock tick.
        await self._redis.zremrangebyscore(rkey, 0, now - self.window_seconds)
        await self._redis.zadd(rkey, {f"{now}:{uuid.uuid4().hex}": now})
        # Let Redis reclaim the key once the whole window has passed.
        await self._redis.expire(rkey, self.window_seconds)

    async def clear(self, key: str) -> None:
        await self._redis.delete(self._key(key))


__all__ = ["RedisLoginRateLimiter"]
