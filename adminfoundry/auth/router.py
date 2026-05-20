from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.audit import (
    LOGIN_FAILURE,
    LOGIN_SUCCESS,
    LOGOUT_ALL,
    record_audit,
    record_audit_in_session,
    request_audit_kwargs,
)
from adminfoundry.auth.dependencies import get_current_user
from adminfoundry.auth.password import verify_password
from adminfoundry.auth.rate_limiter import InMemoryLoginRateLimiter
from adminfoundry.auth.schemas import LoginRequest, MeResponse, TokenResponse
from adminfoundry.auth.tokens import create_access_token
from adminfoundry.db.dependencies import get_async_session
from adminfoundry.models.user import User

router = APIRouter()

_login_limiter = InMemoryLoginRateLimiter()


async def _audit_login(
    request: Request,
    *,
    action: str,
    status_code: int,
    email: str,
    user: User | None = None,
    reason: str | None = None,
) -> None:
    """Audit a login attempt using an isolated session.

    Login uses an isolated audit session (not the request session) so the
    audit row commits even when the request raises (rate-limit / bad
    credentials / inactive user). Safe on SQLite because the login request
    session has only issued a SELECT — no writer lock to contend with.
    """
    changes: dict[str, str] = {"email": email}
    if reason is not None:
        changes["reason"] = reason
    await record_audit(
        request.app.state.adminfoundry.db,
        action=action,
        actor=user,
        changes=changes,
        **request_audit_kwargs(request, status_code=status_code),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    email_key = payload.email.lower()

    if await _login_limiter.is_limited(email_key):
        await _audit_login(
            request,
            action=LOGIN_FAILURE,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            email=payload.email,
            reason="rate_limited",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts.",
        )

    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        await _login_limiter.record_failure(email_key)
        await _audit_login(
            request,
            action=LOGIN_FAILURE,
            status_code=status.HTTP_401_UNAUTHORIZED,
            email=payload.email,
            user=user,
            reason="invalid_credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    if not user.is_active:
        await _login_limiter.record_failure(email_key)
        await _audit_login(
            request,
            action=LOGIN_FAILURE,
            status_code=status.HTTP_403_FORBIDDEN,
            email=payload.email,
            user=user,
            reason="inactive_user",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive.",
        )

    await _login_limiter.clear(email_key)

    config = request.app.state.adminfoundry.config

    token = create_access_token(
        user.id,
        secret_key=config.secret_key,
        algorithm=config.jwt_algorithm,
        expires_minutes=config.access_token_expire_minutes,
        token_version=user.token_version,
    )

    await _audit_login(
        request,
        action=LOGIN_SUCCESS,
        status_code=200,
        email=payload.email,
        user=user,
    )

    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
async def me(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> MeResponse:
    return MeResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superadmin=current_user.is_superadmin,
        is_impersonating=bool(getattr(request.state, "is_impersonating", False)),
    )


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """Revoke every access token previously issued to the current user.

    Implementation: bumps ``User.token_version``. Every token in the wild
    carries a ``tkv`` claim; ``get_current_user`` rejects with 401 when
    they no longer match. Single-token logout (per-jti revocation) is
    deliberately out of scope — see ``docs/security.md``.
    """
    current_user.token_version = (current_user.token_version or 0) + 1
    await session.flush()

    await record_audit_in_session(
        session,
        action=LOGOUT_ALL,
        actor=current_user,
        # Key name avoids "token" / "secret" so the sanitizer leaves it alone.
        changes={"bumped_to": current_user.token_version},
        **request_audit_kwargs(request, status_code=status.HTTP_200_OK),
    )

    return {"detail": "All sessions invalidated."}
