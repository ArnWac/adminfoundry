from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from adminfoundry.database import get_db

router = APIRouter(tags=["health"])


async def _check_db(db: AsyncSession) -> str:
    try:
        await db.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "degraded"


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_status = await _check_db(db)
    return {"status": db_status, "db": db_status}


@router.get("/health/dashboard")
async def health_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Aggregated ops view: DB, active sessions, rate-limit summary, extension health."""
    db_status = await _check_db(db)

    # Active sessions
    try:
        from adminfoundry.services.session_security import session_security
        active_sessions = sum(1 for s in session_security._sessions.values() if s.is_active)
    except Exception:
        active_sessions = None

    # Extension health summary — queried generically via registry, no concrete imports.
    extension_health: list[dict] | None = None
    runtime = getattr(request.app.state, "adminfoundry", None)
    if runtime is not None:
        try:
            extension_health = runtime.extension_registry.health_summary()
        except Exception:
            extension_health = None

    # Rate-limit config summary
    rate_limit_info: dict | None = None
    try:
        from adminfoundry.middleware.rate_limit import get_rate_limit_stats
        rate_limit_info = get_rate_limit_stats()
    except Exception:
        pass

    overall = "ok" if db_status == "ok" else "degraded"
    return {
        "status": overall,
        "db": db_status,
        "active_sessions": active_sessions,
        "rate_limit": rate_limit_info,
        "extensions": extension_health,
    }


