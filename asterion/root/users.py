"""Root user admin endpoints — list + read global users.

Superadmin-only. Hand-written response model so secret columns
(``hashed_password``, ``token_version``) never leak.

The list endpoint goes through ``runtime.providers.users.list_users``
(Roadmap 2.5) so a deployment running an external UserProvider sees
ITS users in the root panel, not just the builtin ``User`` table. The
read-by-id endpoint stays on the builtin model — fetching an arbitrary
(possibly inactive) user by id for the superadmin panel is a builtin-
root concern the provider protocol intentionally doesn't cover
(``get_by_id`` filters inactive for the auth path).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.audit import (
    SUBJECT_EXPORT,
    SUBJECT_REQUEST_LOG,
    USER_ANONYMIZE,
    record_audit_in_session,
    request_audit_kwargs,
)
from asterion.auth.dependencies import require_superadmin
from asterion.db.dependencies import get_async_session
from asterion.models.user import User
from asterion.privacy.anonymizer import anonymize_audit_actor, anonymize_user
from asterion.privacy.export import (
    SubjectNotFoundError,
    SubjectRequestType,
    export_subject,
    list_subject_requests,
    record_subject_request,
)
from asterion.providers.base import AdminPrincipal, UserQuery

router = APIRouter()


class UserOut(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    is_active: bool
    is_superadmin: bool

    @classmethod
    def from_orm_user(cls, user: User) -> UserOut:
        return cls(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superadmin=user.is_superadmin,
        )

    @classmethod
    def from_principal(cls, principal: AdminPrincipal) -> UserOut:
        return cls(
            id=str(principal.id),
            email=principal.email,
            full_name=principal.display_name,
            is_active=principal.is_active,
            is_superadmin=principal.is_superadmin,
        )


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
    limit: int
    offset: int


class AnonymizeResponse(BaseModel):
    id: str
    anonymized: bool = True
    #: How many public audit rows had the user's actor PII redacted.
    audit_rows_redacted: int


@router.get("/users", response_model=UserListResponse)
async def list_users(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
    _current: User = Depends(require_superadmin),
) -> UserListResponse:
    provider = request.app.state.asterion.providers.users
    list_fn = getattr(provider, "list_users", None)
    if list_fn is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="The configured UserProvider does not support listing users.",
        )

    page = await list_fn(
        UserQuery(search=search, limit=limit, offset=offset),
        request=request,
    )
    return UserListResponse(
        items=[UserOut.from_principal(p) for p in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
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


@router.delete("/users/{user_id}", response_model=AnonymizeResponse)
async def anonymize_user_endpoint(
    user_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current: User = Depends(require_superadmin),
) -> AnonymizeResponse:
    """Irreversibly anonymise a user (DSGVO Art. 17) — **not** a hard delete.

    PII on the ``users`` row and the user's public audit-actor fields
    (``actor_label`` e-mail, ``ip_address``) are tombstoned; the rows themselves
    survive so foreign-key / audit integrity holds. For the reversible stage-1
    deactivation use the ``user disable`` CLI command instead.

    Superadmin-only (``require_superadmin`` rejects impersonation tokens). A
    superadmin cannot anonymise their own account.
    """
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    if user.id == current.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot anonymise your own account.",
        )

    anonymize_user(user)
    redacted = await anonymize_audit_actor(session, user_id)
    await session.flush()

    await record_audit_in_session(
        session,
        action=USER_ANONYMIZE,
        actor=current,
        resource="users",
        record_id=user_id,
        changes={"user_id": str(user_id), "audit_rows_redacted": redacted},
        **request_audit_kwargs(request, status_code=200),
    )
    return AnonymizeResponse(id=str(user_id), audit_rows_redacted=redacted)


# ---------------------------------------------------------------------------
# Data-subject rights (G8, DSGVO Art. 15/16/17/18/20)
# ---------------------------------------------------------------------------


class SubjectRequestIn(BaseModel):
    request_type: SubjectRequestType
    status: str = "received"
    note: str | None = None


@router.get("/users/{user_id}/export")
async def export_user_data(
    user_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current: User = Depends(require_superadmin),
) -> dict[str, Any]:
    """Export everything asterion holds about a user (Art. 15/20).

    Returns a JSON bundle of the user's public/global data (their ``users`` row
    minus secrets, memberships, audit actions, impersonation rows, saved filters,
    and DSAR history). Tenant-local business data is out of scope to preserve
    tenant isolation. The export itself is logged: a ``subject_export`` audit row
    **and** a completed ``access`` DSAR entry, so fulfilling the right of access
    is itself accountable.
    """
    runtime = request.app.state.asterion
    try:
        bundle = await export_subject(runtime.db, user_id)
    except SubjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        ) from exc

    await record_subject_request(
        runtime.db,
        subject_user_id=user_id,
        request_type="access",
        status="completed",
        handled_by_user_id=current.id,
        note="Data export generated via root API.",
    )
    await record_audit_in_session(
        session,
        action=SUBJECT_EXPORT,
        actor=current,
        resource="users",
        record_id=user_id,
        changes={"subject_user_id": str(user_id)},
        **request_audit_kwargs(request, status_code=200),
    )
    return bundle


@router.get("/users/{user_id}/dsar")
async def list_user_dsar(
    user_id: uuid.UUID,
    request: Request,
    _current: User = Depends(require_superadmin),
) -> list[dict[str, Any]]:
    """List the DSAR log for a data subject (the accountability register)."""
    runtime = request.app.state.asterion
    return await list_subject_requests(runtime.db, user_id)


@router.post("/users/{user_id}/dsar", status_code=status.HTTP_201_CREATED)
async def create_user_dsar(
    user_id: uuid.UUID,
    payload: SubjectRequestIn,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current: User = Depends(require_superadmin),
) -> dict[str, Any]:
    """Record a data-subject request (Art. 16/17/18 tracking).

    For *erasure* this logs the request — the actual anonymisation is the
    separate ``DELETE /users/{id}`` (Art. 17); for *restriction* the operator
    pairs this entry with ``user disable`` (the documented marker). Validation of
    ``request_type`` / ``status`` happens in the service layer.
    """
    user_exists = (
        await session.execute(select(User.id).where(User.id == user_id))
    ).scalar_one_or_none()
    if user_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    try:
        row = await record_subject_request(
            request.app.state.asterion.db,
            subject_user_id=user_id,
            request_type=payload.request_type,
            status=payload.status,  # type: ignore[arg-type]
            handled_by_user_id=current.id,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    await record_audit_in_session(
        session,
        action=SUBJECT_REQUEST_LOG,
        actor=current,
        resource="users",
        record_id=user_id,
        changes={"subject_user_id": str(user_id), "request_type": payload.request_type},
        **request_audit_kwargs(request, status_code=201),
    )
    return row
