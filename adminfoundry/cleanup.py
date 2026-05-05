import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import delete

from adminfoundry.database import AsyncSessionLocal
from adminfoundry.models.revoked_token import RevokedToken
from adminfoundry.models.rate_limit import RateLimitRequest
from adminfoundry.models.password_reset_token import PasswordResetToken

logger = logging.getLogger(__name__)

# Rows older than this are guaranteed to be outside any sliding window
_RATE_LIMIT_MAX_WINDOW_SECONDS = 300


async def _run_cleanup() -> None:
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        await db.execute(delete(RevokedToken).where(RevokedToken.exp < now))
        cutoff_ts = time.time() - _RATE_LIMIT_MAX_WINDOW_SECONDS
        await db.execute(delete(RateLimitRequest).where(RateLimitRequest.ts < cutoff_ts))
        await db.execute(delete(PasswordResetToken).where(PasswordResetToken.expires_at < now))
        await db.commit()


async def periodic_cleanup(interval_seconds: int = 3600) -> None:
    """Background task: purge expired revoked tokens and stale rate-limit rows."""
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await _run_cleanup()
        except Exception:
            logger.exception("Cleanup task failed")
