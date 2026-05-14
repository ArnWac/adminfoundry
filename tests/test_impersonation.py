"""Impersonation token flow tests.

Split from test_auth_tokens.py.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from adminfoundry.models.user import User
from adminfoundry.models.tenant import Tenant
from adminfoundry.models.impersonation_log import ImpersonationLog
from adminfoundry.auth import create_access_token, create_impersonation_token, hash_password


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


@pytest_asyncio.fixture
async def tenant(db: AsyncSession) -> Tenant:
    t = Tenant(name="Acme Corp", slug="acme", is_active=True)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


@pytest_asyncio.fixture
async def plain_user(db: AsyncSession) -> User:
    u = User(
        email="plain@acme.com",
        hashed_password=hash_password("pw"),
        is_active=True,
        is_superadmin=False,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Impersonation token restrictions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_impersonation_token_cannot_be_refreshed(client: AsyncClient, superadmin: User, db: AsyncSession):
    """Impersonation tokens are access-type; passing one as refresh token must fail."""
    imp_token, _ = create_impersonation_token(str(superadmin.id), str(superadmin.id), "00000000-0000-0000-0000-000000000000")
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": imp_token})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_impersonation_token_returns_tenant_scoped_registry(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    """Impersonation token may read the admin registry but only sees tenant-scoped models."""
    imp_token, _ = create_impersonation_token(str(superadmin.id), str(superadmin.id), "00000000-0000-0000-0000-000000000000")
    resp = await client.get(
        "/api/v1/admin",
        headers={"Authorization": f"Bearer {imp_token}"},
    )
    assert resp.status_code == 200
    model_names = [m["model"] for m in resp.json()["models"]]
    assert "users" not in model_names        # tenant_scoped=False — excluded
    assert "audit_logs" not in model_names   # tenant_scoped=False — excluded


@pytest.mark.asyncio
async def test_impersonation_token_rejected_on_write_superadmin_route(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    """Impersonation token must not access write superadmin-only routes (e.g. user create)."""
    from uuid import uuid4
    imp_token, _ = create_impersonation_token(str(superadmin.id), str(superadmin.id), "00000000-0000-0000-0000-000000000000")
    resp = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {imp_token}"},
        json={"email": f"x{uuid4()}@x.com", "password": "pw"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_impersonation_token_allows_normal_route(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    """Impersonation token is valid for non-superadmin routes like /me."""
    imp_token, _ = create_impersonation_token(str(superadmin.id), str(superadmin.id), "00000000-0000-0000-0000-000000000000")
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {imp_token}"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Impersonation flow: create tenant -> impersonate -> revoke -> rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_impersonate_creates_log(
    client: AsyncClient, superadmin: User, tenant: Tenant, plain_user: User, db: AsyncSession
):
    resp = await client.post(
        f"/api/v1/tenants/{tenant.id}/impersonate",
        headers=auth(superadmin),
        json={"target_user_id": str(plain_user.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "impersonation_log_id" in data

    log = (
        await db.execute(select(ImpersonationLog).where(ImpersonationLog.id == data["impersonation_log_id"]))
    ).scalar_one_or_none()
    assert log is not None
    assert str(log.superadmin_id) == str(superadmin.id)
    assert str(log.target_user_id) == str(plain_user.id)
    assert log.revoked_at is None


@pytest.mark.asyncio
async def test_revoke_impersonation_blacklists_token(
    client: AsyncClient, superadmin: User, tenant: Tenant, plain_user: User, db: AsyncSession
):
    imp_resp = await client.post(
        f"/api/v1/tenants/{tenant.id}/impersonate",
        headers=auth(superadmin),
        json={"target_user_id": str(plain_user.id)},
    )
    data = imp_resp.json()
    imp_token = data["access_token"]

    log = (
        await db.execute(select(ImpersonationLog).where(ImpersonationLog.id == data["impersonation_log_id"]))
    ).scalar_one()
    jti = log.jti

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {imp_token}"})
    assert me.status_code == 200

    revoke = await client.post(
        f"/api/v1/tenants/{tenant.id}/impersonate/revoke",
        headers=auth(superadmin),
        json={"jti": jti},
    )
    assert revoke.status_code == 200

    me_after = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {imp_token}"})
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_revoke_marks_log_revoked(
    client: AsyncClient, superadmin: User, tenant: Tenant, plain_user: User, db: AsyncSession
):
    imp_resp = await client.post(
        f"/api/v1/tenants/{tenant.id}/impersonate",
        headers=auth(superadmin),
        json={"target_user_id": str(plain_user.id)},
    )
    log_id = imp_resp.json()["impersonation_log_id"]
    log = (await db.execute(select(ImpersonationLog).where(ImpersonationLog.id == log_id))).scalar_one()

    await client.post(
        f"/api/v1/tenants/{tenant.id}/impersonate/revoke",
        headers=auth(superadmin),
        json={"jti": log.jti},
    )

    await db.refresh(log)
    assert log.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_twice_returns_conflict(
    client: AsyncClient, superadmin: User, tenant: Tenant, plain_user: User, db: AsyncSession
):
    imp_resp = await client.post(
        f"/api/v1/tenants/{tenant.id}/impersonate",
        headers=auth(superadmin),
        json={"target_user_id": str(plain_user.id)},
    )
    log_id = imp_resp.json()["impersonation_log_id"]
    log = (await db.execute(select(ImpersonationLog).where(ImpersonationLog.id == log_id))).scalar_one()

    await client.post(
        f"/api/v1/tenants/{tenant.id}/impersonate/revoke",
        headers=auth(superadmin),
        json={"jti": log.jti},
    )
    resp2 = await client.post(
        f"/api/v1/tenants/{tenant.id}/impersonate/revoke",
        headers=auth(superadmin),
        json={"jti": log.jti},
    )
    assert resp2.status_code == 409
