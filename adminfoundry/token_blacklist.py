from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from adminfoundry.models.revoked_token import RevokedToken


async def blacklist_token(jti: str, exp: float | int, db: AsyncSession) -> None:
    exp_dt = datetime.fromtimestamp(float(exp), tz=timezone.utc)
    db.add(RevokedToken(jti=jti, exp=exp_dt))
    await db.flush()


async def is_blacklisted(jti: str, db: AsyncSession) -> bool:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RevokedToken).where(
            RevokedToken.jti == jti,
            RevokedToken.exp > now,
        )
    )
    return result.scalar_one_or_none() is not None


def clear_blacklist() -> None:
    """No-op — DB cleanup is handled by the clean_tables test fixture."""
