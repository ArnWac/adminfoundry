"""Tests for TenantAuthContext permission checking."""

from __future__ import annotations

import uuid

from adminfoundry.tenancy.context import TenantAuthContext, TenantContext


def _tenant():
    return TenantContext(
        id=uuid.uuid4(),
        slug="acme",
        name="Acme Corp",
        is_active=True,
        schema_name="tenant_acme",
    )


class _FakeMembership:
    id = uuid.uuid4()


class _FakeRole:
    name: str
    permissions: list

    def __init__(self, name):
        self.name = name
        self.permissions = []


def _auth(permission_keys=None, roles=None):
    return TenantAuthContext(
        tenant=_tenant(),
        membership=_FakeMembership(),
        roles=roles or [],
        permission_keys=set(permission_keys or []),
    )


def test_has_permission_exact_match():
    auth = _auth(permission_keys=["admin.users.list"])
    assert auth.has_permission("admin.users.list") is True


def test_has_permission_miss():
    auth = _auth(permission_keys=["admin.users.list"])
    assert auth.has_permission("admin.users.delete") is False


def test_has_role_match():
    role = _FakeRole("admin")
    auth = _auth(roles=[role])
    assert auth.has_role("admin") is True


def test_has_role_miss():
    auth = _auth()
    assert auth.has_role("owner") is False


def test_role_names_returns_frozenset():
    roles = [_FakeRole("owner"), _FakeRole("viewer")]
    auth = _auth(roles=roles)
    names = auth.role_names()
    assert "owner" in names
    assert "viewer" in names


def test_tenant_context_from_dict():
    data = {
        "id": str(uuid.uuid4()),
        "slug": "test",
        "name": "Test",
        "is_active": True,
        "timezone": None,
        "language": None,
        "date_format": None,
        "date_pattern": None,
        "allowed_cidrs": None,
    }
    ctx = TenantContext.from_dict(data)
    assert ctx.slug == "test"
    assert ctx.schema_name == "tenant_test"
