"""
Password reset endpoint tests.

Covers: silent 204 for unknown email, token creation for known email,
confirm with valid/expired/used/invalid token, inactive user rejection,
and disabled feature (404).
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.auth import hash_password, verify_password
from adminfoundry.models.password_reset_token import PasswordResetToken
from adminfoundry.models.user import User


def _active_user_fixture(db, email="reset@example.com"):
    user = User(
        email=email,
        hashed_password=hash_password("oldpass123"),
        full_name="Reset User",
        is_active=True,
        is_superadmin=False,
    )
    db.add(user)
    return user


# ---------------------------------------------------------------------------
# Request endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_request_unknown_email_silent(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_reset_request_known_email_creates_token(
    client: AsyncClient, db: AsyncSession
):
    user = _active_user_fixture(db)
    await db.commit()
    await db.refresh(user)

    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": user.email},
    )
    assert resp.status_code == 204

    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    token_row = result.scalar_one_or_none()
    assert token_row is not None
    assert token_row.used is False
    expires = token_row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    assert expires > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_reset_request_disabled_returns_404(
    client: AsyncClient, db: AsyncSession, monkeypatch
):
    from adminfoundry import settings as _settings_mod
    monkeypatch.setattr(_settings_mod.settings, "PASSWORD_RESET_ENABLED", False)

    user = _active_user_fixture(db)
    await db.commit()

    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": user.email},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Confirm endpoint
# ---------------------------------------------------------------------------

async def _make_token(db: AsyncSession, user: User, *, used=False, expired=False) -> str:
    import secrets
    raw = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) - timedelta(hours=1)
        if expired
        else datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db.add(PasswordResetToken(token=raw, user_id=user.id, expires_at=expires_at, used=used))
    await db.commit()
    return raw


@pytest.mark.asyncio
async def test_reset_confirm_valid_token_changes_password(
    client: AsyncClient, db: AsyncSession
):
    user = _active_user_fixture(db)
    await db.commit()
    await db.refresh(user)
    token = await _make_token(db, user)

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpass456"},
    )
    assert resp.status_code == 204

    await db.refresh(user)
    assert verify_password("newpass456", user.hashed_password)


@pytest.mark.asyncio
async def test_reset_confirm_marks_token_used(
    client: AsyncClient, db: AsyncSession
):
    user = _active_user_fixture(db)
    await db.commit()
    await db.refresh(user)
    token = await _make_token(db, user)

    await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpass456"},
    )

    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    record = result.scalar_one()
    assert record.used is True


@pytest.mark.asyncio
async def test_reset_confirm_expired_token_rejected(
    client: AsyncClient, db: AsyncSession
):
    user = _active_user_fixture(db)
    await db.commit()
    await db.refresh(user)
    token = await _make_token(db, user, expired=True)

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpass456"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_confirm_used_token_rejected(
    client: AsyncClient, db: AsyncSession
):
    user = _active_user_fixture(db)
    await db.commit()
    await db.refresh(user)
    token = await _make_token(db, user, used=True)

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpass456"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_confirm_invalid_token_rejected(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "completelywrong", "new_password": "newpass456"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_confirm_inactive_user_rejected(
    client: AsyncClient, db: AsyncSession
):
    user = User(
        email="inactive2@example.com",
        hashed_password=hash_password("oldpass123"),
        is_active=False,
        is_superadmin=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = await _make_token(db, user)

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpass456"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_confirm_disabled_returns_404(client: AsyncClient, monkeypatch):
    from adminfoundry import settings as _settings_mod
    monkeypatch.setattr(_settings_mod.settings, "PASSWORD_RESET_ENABLED", False)

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "anytoken", "new_password": "newpass456"},
    )
    assert resp.status_code == 404
