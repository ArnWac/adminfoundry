"""Audit log listing + tenant-scoped audit writes.

Split from test_auth_tokens.py.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from adminfoundry.models.user import User
from adminfoundry.models.tenant import Tenant
from adminfoundry.models.audit_log import AuditLog
from adminfoundry.models.role import Role
from adminfoundry.auth import create_access_token, create_impersonation_token, hash_password


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


# ---------------------------------------------------------------------------
# Audit log listing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_list(client: AsyncClient, superadmin: User, db: AsyncSession):
    resp = await client.get("/api/v1/audit", headers=auth(superadmin))
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_audit_log_requires_superadmin(client: AsyncClient, db: AsyncSession):
    user = User(
        email="plain3@x.com",
        hashed_password=hash_password("pw"),
        is_active=True,
        is_superadmin=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    resp = await client.get("/api/v1/audit", headers=auth(user))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Same-origin impersonation: tenant_id in audit log + dashboard filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_impersonation_started_audit_has_tenant_id(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    """impersonation_started audit log entry must carry the target tenant_id."""
    tenant = Tenant(name="Imp Tenant", slug="imp-tenant", is_active=True)
    plain = User(
        email="plain@imp.com",
        hashed_password=hash_password("pw"),
        is_active=True,
        is_superadmin=False,
    )
    db.add(tenant)
    db.add(plain)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(plain)

    resp = await client.post(
        f"/api/v1/tenants/{tenant.id}/impersonate",
        headers=auth(superadmin),
        json={"target_user_id": str(plain.id)},
    )
    assert resp.status_code == 200

    log = (await db.execute(
        select(AuditLog).where(AuditLog.action == "impersonation_started")
    )).scalar_one_or_none()
    assert log is not None
    assert log.tenant_id == tenant.id
    assert log.actor == superadmin.email


@pytest.mark.asyncio
async def test_audit_log_tenant_id_from_impersonation_token(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    """Audit log entries must carry tenant_id when written via a same-origin impersonation
    token — i.e. when TenantMiddleware did not set request.state.tenant."""
    tenant = Tenant(name="Audit Tenant", slug="audit-tenant", is_active=True)
    role = Role(name="imp-audit-role")
    db.add(tenant)
    db.add(role)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(role)

    imp_token, _ = create_impersonation_token(
        str(superadmin.id), str(superadmin.id), str(tenant.id)
    )
    resp = await client.put(
        f"/api/v1/admin/permission-matrix/{role.id}",
        headers={"Authorization": f"Bearer {imp_token}"},
        json=[{
            "model_name": "roles",
            "can_list": True, "can_create": False, "can_update": False, "can_delete": False,
        }],
    )
    assert resp.status_code == 204

    log = (await db.execute(
        select(AuditLog)
        .where(AuditLog.object_id == str(role.id), AuditLog.action == "updated")
    )).scalar_one_or_none()
    assert log is not None
    assert log.tenant_id == tenant.id


@pytest.mark.asyncio
async def test_dashboard_hides_global_models_during_impersonation(
    client: AsyncClient, superadmin: User, db: AsyncSession
):
    """ModelCountsWidget must omit tenant_scoped=False models (users, audit_logs, tenants)
    when the superadmin is using a same-origin impersonation token."""
    tenant = Tenant(name="Dash Tenant", slug="dash-tenant", is_active=True)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    imp_token, _ = create_impersonation_token(
        str(superadmin.id), str(superadmin.id), str(tenant.id)
    )
    resp = await client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {imp_token}"},
    )
    assert resp.status_code == 200
    widgets = resp.json()["widgets"]
    counts = next((w for w in widgets if w["type"] == "counts"), None)
    if counts:  # widget only present when models are registered
        model_names = [r["model"] for r in counts["data"]["rows"]]
        assert "users" not in model_names       # tenant_scoped=False — must be hidden
        assert "audit_logs" not in model_names  # tenant_scoped=False — must be hidden
