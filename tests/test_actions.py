"""Tests for the generic actions shipped with adminfoundry."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.actions import (
    ActivateUsersAction,
    BulkDeleteAction,
    DeactivateUsersAction,
    DisableTenantAction,
    EnableTenantAction,
)
from adminfoundry.auth import hash_password
from adminfoundry.models.tenant import Tenant
from adminfoundry.models.user import User


async def _make_user(db: AsyncSession, email: str, *, active: bool) -> User:
    u = User(
        email=email,
        hashed_password=hash_password("pw"),
        is_active=active,
        is_superadmin=False,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.mark.asyncio
async def test_activate_users_action(db: AsyncSession, superadmin: User):
    u = await _make_user(db, "act@example.com", active=False)
    result = await ActivateUsersAction().execute([u], db, superadmin)
    assert result["affected"] == 1
    await db.refresh(u)
    assert u.is_active is True


@pytest.mark.asyncio
@pytest.mark.parametrize("n_users", [1, 2])
async def test_deactivate_users_action(db: AsyncSession, superadmin: User, n_users: int):
    users = [
        await _make_user(db, f"deact{i}@example.com", active=True)
        for i in range(n_users)
    ]
    result = await DeactivateUsersAction().execute(users, db, superadmin)
    assert result["affected"] == n_users
    for u in users:
        await db.refresh(u)
        assert u.is_active is False


@pytest.mark.asyncio
async def test_bulk_delete_action(db: AsyncSession, superadmin: User):
    u1 = await _make_user(db, "d1@example.com", active=True)
    u2 = await _make_user(db, "d2@example.com", active=True)
    result = await BulkDeleteAction().execute([u1, u2], db, superadmin)
    assert result["affected"] == 2


@pytest.mark.asyncio
async def test_enable_disable_tenant_actions(db: AsyncSession, superadmin: User):
    t = Tenant(name="Acme", slug="acme", is_active=True)
    db.add(t)
    await db.commit()
    await db.refresh(t)

    await DisableTenantAction().execute([t], db, superadmin)
    await db.refresh(t)
    assert t.is_active is False

    await EnableTenantAction().execute([t], db, superadmin)
    await db.refresh(t)
    assert t.is_active is True


def test_action_metadata_shape():
    a = BulkDeleteAction()
    meta = a.to_dict()
    assert meta["name"] == "delete"
    assert meta["danger"] is True
    assert meta["confirm"] is True
    assert meta["bulk"] is True
    assert meta["single"] is False
