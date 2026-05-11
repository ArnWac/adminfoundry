"""Tests for GDPR compliance endpoints and 2FA."""
import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from adminfoundry.auth import create_access_token, create_mfa_token
from adminfoundry.auth import hash_password
from adminfoundry.models.audit_log import AuditLog
from adminfoundry.models.user import User


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


# ---------------------------------------------------------------------------
# 2FA setup / enable / disable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_2fa_setup_returns_uri_and_backup_codes(client: AsyncClient, superadmin: User):
    resp = await client.post("/api/v1/auth/2fa/setup", headers=auth(superadmin))
    assert resp.status_code == 200
    data = resp.json()
    assert data["totp_uri"].startswith("otpauth://totp/")
    assert len(data["backup_codes"]) == 8


@pytest.mark.asyncio
async def test_2fa_enable_with_valid_code(client: AsyncClient, superadmin: User, db: AsyncSession):
    # Setup
    resp = await client.post("/api/v1/auth/2fa/setup", headers=auth(superadmin))
    assert resp.status_code == 200

    # Reload to get the stored secret
    await db.refresh(superadmin)
    code = pyotp.TOTP(superadmin.totp_secret).now()

    resp = await client.post("/api/v1/auth/2fa/enable", headers=auth(superadmin),
                             json={"mfa_token": "", "code": code})
    assert resp.status_code == 200
    await db.refresh(superadmin)
    assert superadmin.totp_enabled is True


@pytest.mark.asyncio
async def test_2fa_enable_with_invalid_code_fails(client: AsyncClient, superadmin: User, db: AsyncSession):
    await client.post("/api/v1/auth/2fa/setup", headers=auth(superadmin))
    resp = await client.post("/api/v1/auth/2fa/enable", headers=auth(superadmin),
                             json={"mfa_token": "", "code": "000000"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_2fa_disable(client: AsyncClient, superadmin: User, db: AsyncSession):
    await client.post("/api/v1/auth/2fa/setup", headers=auth(superadmin))
    await db.refresh(superadmin)
    code = pyotp.TOTP(superadmin.totp_secret).now()
    await client.post("/api/v1/auth/2fa/enable", headers=auth(superadmin),
                      json={"mfa_token": "", "code": code})

    await db.refresh(superadmin)
    code2 = pyotp.TOTP(superadmin.totp_secret).now()
    resp = await client.post("/api/v1/auth/2fa/disable", headers=auth(superadmin),
                             json={"mfa_token": "", "code": code2})
    assert resp.status_code == 200
    await db.refresh(superadmin)
    assert superadmin.totp_enabled is False


# ---------------------------------------------------------------------------
# 2FA login flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_with_2fa_enabled_returns_mfa_challenge(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    # Enable 2FA directly on the model
    secret = pyotp.random_base32()
    superadmin.totp_secret = secret
    superadmin.totp_enabled = True
    await db.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@example.com", "password": "password123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["mfa_required"] is True
    assert data["mfa_token"] is not None
    assert data.get("access_token") is None


@pytest.mark.asyncio
async def test_2fa_verify_with_valid_code_issues_tokens(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    secret = pyotp.random_base32()
    superadmin.totp_secret = secret
    superadmin.totp_enabled = True
    await db.commit()

    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@example.com", "password": "password123"
    })
    mfa_token = login_resp.json()["mfa_token"]
    code = pyotp.TOTP(secret).now()

    resp = await client.post("/api/v1/auth/2fa/verify",
                             json={"mfa_token": mfa_token, "code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] is not None
    assert data["mfa_required"] is False


@pytest.mark.asyncio
async def test_2fa_verify_with_invalid_code_fails(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    secret = pyotp.random_base32()
    superadmin.totp_secret = secret
    superadmin.totp_enabled = True
    await db.commit()

    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@example.com", "password": "password123"
    })
    mfa_token = login_resp.json()["mfa_token"]

    resp = await client.post("/api/v1/auth/2fa/verify",
                             json={"mfa_token": mfa_token, "code": "000000"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_2fa_verify_with_backup_code(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    import hashlib
    secret = pyotp.random_base32()
    backup = "deadbeef"
    superadmin.totp_secret = secret
    superadmin.totp_enabled = True
    superadmin.totp_backup_codes = [hashlib.sha256(backup.encode()).hexdigest()]
    await db.commit()

    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@example.com", "password": "password123"
    })
    mfa_token = login_resp.json()["mfa_token"]

    resp = await client.post("/api/v1/auth/2fa/verify",
                             json={"mfa_token": mfa_token, "code": backup})
    assert resp.status_code == 200
    # Backup code should be consumed
    await db.refresh(superadmin)
    assert not superadmin.totp_backup_codes


# ---------------------------------------------------------------------------
# GDPR: data export
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_me_export_json(client: AsyncClient, superadmin: User):
    resp = await client.get("/api/v1/users/me/export", headers=auth(superadmin))
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == superadmin.email
    assert "audit_log" in data
    assert "exported_at" in data


@pytest.mark.asyncio
async def test_me_export_csv(client: AsyncClient, superadmin: User):
    resp = await client.get("/api/v1/users/me/export?format=csv", headers=auth(superadmin))
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert superadmin.email in resp.text


@pytest.mark.asyncio
async def test_user_export_superadmin(client: AsyncClient, superadmin: User):
    resp = await client.get(f"/api/v1/users/{superadmin.id}/export", headers=auth(superadmin))
    assert resp.status_code == 200
    assert resp.json()["id"] == str(superadmin.id)


# ---------------------------------------------------------------------------
# GDPR: erase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gdpr_erase_deletes_user_and_anonymises_logs(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    # Create a target user and a fake audit log entry
    target = User(
        email="target@example.com",
        hashed_password=hash_password("pw"),
        is_active=True,
    )
    db.add(target)
    await db.flush()

    log = AuditLog(
        method="POST",
        path="/api/v1/something",
        status_code=200,
        user_id=target.id,
        actor=target.email,
        action="created",
        object_id="abc",
    )
    db.add(log)
    await db.commit()
    target_id = target.id
    log_id = log.id

    resp = await client.post(f"/api/v1/users/{target_id}/erase", headers=auth(superadmin))
    assert resp.status_code == 200

    # expire_on_commit=False keeps stale objects in the identity map after commit;
    # expunge_all() forces the next SELECT to actually hit the DB.
    db.expunge_all()

    # User is gone
    gone = (await db.execute(select(User).where(User.id == target_id))).scalar_one_or_none()
    assert gone is None

    # Audit log remains but is anonymised
    remaining = (await db.execute(select(AuditLog).where(AuditLog.id == log_id))).scalar_one_or_none()
    assert remaining is not None
    assert remaining.user_id is None
    assert remaining.actor == "[deleted]"


@pytest.mark.asyncio
async def test_gdpr_erase_requires_superadmin(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    regular = User(
        email="regular@example.com",
        hashed_password=hash_password("pw"),
        is_active=True,
        is_superadmin=False,
    )
    db.add(regular)
    await db.commit()

    resp = await client.post(
        f"/api/v1/users/{superadmin.id}/erase",
        headers={"Authorization": f"Bearer {create_access_token(str(regular.id))}"},
    )
    assert resp.status_code == 403
