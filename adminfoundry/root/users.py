"""Root user admin endpoints — list + read global users.

Superadmin-only. Hand-written response model so secret columns
(``hashed_password``, ``token_version``) never leak.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.auth.dependencies import require_superadmin
from adminfoundry.db.dependencies import get_async_session
from adminfoundry.models.user import User
from adminfoundry.security.validation import validate_limit_offset

router = APIRouter()


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    is_superadmin: bool

    @classmethod
    def from_orm_user(cls, user: User) -> UserOut:
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superadmin=user.is_superadmin,
        )


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
    limit: int
    offset: int


@router.get("/users", response_model=UserListResponse)
async def list_users(
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    _current: User = Depends(require_superadmin),
) -> UserListResponse:
    normalized_limit, normalized_offset = validate_limit_offset(limit=limit, offset=offset)

    base = select(User)
    if search:
        needle = f"%{search.strip()}%"
        base = base.where(or_(User.email.ilike(needle), User.full_name.ilike(needle)))

    total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    rows = (
        (
            await session.execute(
                base.order_by(User.email).limit(normalized_limit).offset(normalized_offset)
            )
        )
        .scalars()
        .all()
    )

    return UserListResponse(
        items=[UserOut.from_orm_user(u) for u in rows],
        total=total,
        limit=normalized_limit,
        offset=normalized_offset,
    )


@router.get("/users/{user_id}", response_model=UserOut)
async def read_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _current: User = Depends(require_superadmin),
) -> UserOut:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return UserOut.from_orm_user(user)
