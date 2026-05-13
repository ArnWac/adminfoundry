import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from adminfoundry.models.revoked_token import RevokedToken
from adminfoundry.models.password_reset_token import PasswordResetToken
from adminfoundry.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def _run_cleanup() -> None:
    from adminfoundry.database import AsyncSessionLocal
    from adminfoundry.settings import settings
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        await db.execute(delete(RevokedToken).where(RevokedToken.exp < now))
        await db.execute(delete(PasswordResetToken).where(PasswordResetToken.expires_at < now))
        if settings.AUDIT_LOG_RETENTION_DAYS > 0:
            cutoff = now - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
            await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        await db.commit()


async def periodic_cleanup(interval_seconds: int = 3600) -> None:
    """Background task: purge expired revoked tokens and stale rate-limit rows."""
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await _run_cleanup()
        except Exception:
            logger.exception("Cleanup task failed")
