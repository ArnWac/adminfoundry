import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from coreAdmin_api.database import get_db
from coreAdmin_api.dependencies import require_superadmin
from coreAdmin_api.models.audit_log import AuditLog
from coreAdmin_api.models.user import User
from coreAdmin_api.schemas.audit import AuditLogPublic
from coreAdmin_api.schemas.common import PaginatedResponse

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=PaginatedResponse[AuditLogPublic])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    total = (await db.execute(select(func.count()).select_from(AuditLog))).scalar_one()
    offset = (page - 1) * page_size
    items = (
        await db.execute(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )
