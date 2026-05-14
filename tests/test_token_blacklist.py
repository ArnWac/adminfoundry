"""Token blacklist unit tests + logout integration tests.

Split from test_auth_tokens.py.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.models.user import User
from adminfoundry.token_blacklist import blacklist_token, is_blacklisted


# ---------------------------------------------------------------------------
# Unit: token blacklist
# ---------------------------------------------------------------------------

async def test_blacklist_token_is_detected(db: AsyncSession):
    import time
    jti = "test-jti-1"
    exp = time.time() + 3600
    await blacklist_token(jti, exp, db)
    assert await is_blacklisted(jti, db) is True


async def test_blacklist_expired_token_is_not_blocked(db: AsyncSession):
    import time
    jti = "test-jti-2"
    exp = time.time() - 1  # already expired
    await blacklist_token(jti, exp, db)
    assert await is_blacklisted(jti, db) is False


async def test_unknown_jti_is_not_blacklisted(db: AsyncSession):
    assert await is_blacklisted("never-seen-jti", db) is False


# ---------------------------------------------------------------------------
# Logout — e2e flow: login -> logout -> same token rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_invalidates_access_token(client: AsyncClient, superadmin: User):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    access_token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200

    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204

    me_after = await client.get("/api/v1/auth/me", headers=headers)
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_refresh_still_works_after_logout(client: AsyncClient, superadmin: User):
    """Logout revokes access token only; refresh token remains valid."""
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    access_token = login.json()["access_token"]
    refresh_token = login.json()["refresh_token"]

    await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
