import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.database import get_db
from adminfoundry.pagination import paginate
from adminfoundry.dependencies import get_current_user, require_superadmin
from adminfoundry.extensions.jobs.models import Job
from adminfoundry.extensions.jobs.schemas import JobRead
from adminfoundry.extensions.jobs.service import job_service
from adminfoundry.models.user import User

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    stmt = select(Job).order_by(Job.created_at.desc())
    jobs, total, pages = await paginate(db, stmt, page, page_size)
    return {
        "items": [JobRead.model_validate(j).model_dump() for j in jobs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await job_service.get_by_id(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not current_user.is_superadmin and str(job.initiator_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return JobRead.model_validate(job)
