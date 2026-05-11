import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from adminfoundry.database import get_db
from adminfoundry.pagination import paginate
from adminfoundry.dependencies import require_superadmin
from adminfoundry.models.audit_log import AuditLog
from adminfoundry.models.user import User
from adminfoundry.models.password_reset_token import PasswordResetToken
from adminfoundry.auth import hash_password, verify_password
from adminfoundry.dependencies import get_current_user
from adminfoundry.schemas.common import PaginatedResponse
from adminfoundry.schemas.user import UserPublic, UserCreate, UserUpdate, ProfileUpdate, UserExportResponse, AuditLogExport, SelfEraseRequest

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=PaginatedResponse[UserPublic])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    items, total, pages = await paginate(db, select(User), page, page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_active=True,
        is_superadmin=body.is_superadmin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserPublic)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch("/me", response_model=UserPublic)
async def update_me(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.new_password is not None or body.current_password is not None:
        if not body.current_password or not body.new_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Both current_password and new_password are required")
        if not verify_password(body.current_password, current_user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Current password is incorrect")
        current_user.hashed_password = hash_password(body.new_password)

    if body.email is not None and body.email != current_user.email:
        conflict = (await db.execute(
            select(User).where(User.email == body.email, User.id != current_user.id)
        )).scalar_one_or_none()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        current_user.email = body.email

    if body.full_name is not None:
        current_user.full_name = body.full_name

    await db.commit()
    await db.refresh(current_user)
    return current_user


# ---------------------------------------------------------------------------
# GDPR self-service (Art. 15 / 17 / 20 DSGVO) — must be before /{user_id} routes
# ---------------------------------------------------------------------------

@router.get("/me/export")
async def export_my_data(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Art. 15 / 20 DSGVO — machine-readable export of all personal data."""
    return await _build_export(current_user, format, db)


@router.post("/me/erase", status_code=status.HTTP_200_OK)
async def self_erase(
    body: SelfEraseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Art. 17 DSGVO — self-service erasure with password confirmation."""
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password")

    user_id = current_user.id
    await db.execute(
        update(AuditLog)
        .where(AuditLog.user_id == user_id)
        .values(user_id=None, actor="[deleted]")
    )
    from sqlalchemy import delete as _delete
    await db.execute(_delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id))
    await db.delete(current_user)
    await db.commit()
    return {"status": "erased", "user_id": str(user_id)}


# ---------------------------------------------------------------------------
# Superadmin user management
# ---------------------------------------------------------------------------

@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    changes = body.model_dump(exclude_none=True)
    privilege_changed = "is_active" in changes or "is_superadmin" in changes
    for field, value in changes.items():
        setattr(user, field, value)
    if privilege_changed:
        user.token_version += 1

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Deactivate (soft-delete). For full GDPR erasure use POST /{user_id}/erase."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    user.token_version += 1
    await db.commit()


@router.get("/{user_id}/export")
async def export_user_data(
    user_id: uuid.UUID,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Art. 15 DSGVO — full data export for a specific user (superadmin only)."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return await _build_export(user, format, db)


@router.post("/{user_id}/erase", status_code=status.HTTP_200_OK)
async def gdpr_erase_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Art. 17 DSGVO — irreversible erasure: anonymise audit logs, hard-delete user."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Anonymise audit log entries — preserve the log record but break personal link
    await db.execute(
        update(AuditLog)
        .where(AuditLog.user_id == user_id)
        .values(user_id=None, actor="[deleted]")
    )

    # Delete password reset tokens
    await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
    )
    from sqlalchemy import delete as _delete
    await db.execute(_delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id))

    # Hard-delete the user (CASCADE removes user_roles rows)
    await db.delete(user)
    await db.commit()

    return {"status": "erased", "user_id": str(user_id)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _build_export(user: User, format: str, db: AsyncSession):
    logs = (await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(AuditLog.created_at.desc())
    )).scalars().all()

    export = UserExportResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
        roles=[r.name for r in (user.roles or [])],
        audit_log=[AuditLogExport.model_validate(log) for log in logs],
        exported_at=datetime.now(timezone.utc),
    )

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["field", "value"])
        writer.writerow(["id", str(export.id)])
        writer.writerow(["email", export.email])
        writer.writerow(["full_name", export.full_name or ""])
        writer.writerow(["created_at", export.created_at.isoformat()])
        writer.writerow(["roles", ", ".join(export.roles)])
        writer.writerow([])
        writer.writerow(["--- audit log ---"])
        writer.writerow(["created_at", "action", "method", "path", "ip_address"])
        for entry in export.audit_log:
            writer.writerow([
                entry.created_at.isoformat(),
                entry.action or "",
                entry.method,
                entry.path,
                entry.ip_address or "",
            ])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="user_{user.id}.csv"'},
        )

    return export
