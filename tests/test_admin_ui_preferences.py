"""Admin UI preference schema + API endpoints.

Split from test_admin_ui_pages.py.
"""
import pytest
from httpx import AsyncClient

from adminfoundry.admin.ui_preferences import (
    UIPreference,
    get_preferences,
    set_preferences,
    clear_preferences,
)


# ---------------------------------------------------------------------------
# UIPreference schema — unit tests
# ---------------------------------------------------------------------------

def test_preference_defaults():
    p = UIPreference()
    assert p.density == "comfortable"
    assert p.visible_columns == {}
    assert p.sorting == {}
    assert p.navigation_favorites == []


def test_preference_round_trip():
    p = UIPreference(
        density="compact",
        visible_columns={"user": ["email", "is_active"]},
        sorting={"user": "-created_at"},
        navigation_favorites=["user", "tenant"],
    )
    dumped = p.model_dump()
    restored = UIPreference.model_validate(dumped)
    assert restored.density == "compact"
    assert restored.visible_columns["user"] == ["email", "is_active"]
    assert restored.navigation_favorites == ["user", "tenant"]


def test_preference_schema_has_no_security_fields():
    """Schema must not allow encoding permissions or superadmin overrides."""
    fields = UIPreference.model_fields
    for forbidden in ("is_superadmin", "permissions", "roles", "token", "password"):
        assert forbidden not in fields


def test_preference_store_isolation():
    clear_preferences()
    set_preferences("user-1", UIPreference(density="compact"))
    set_preferences("user-2", UIPreference(density="spacious"))
    assert get_preferences("user-1").density == "compact"
    assert get_preferences("user-2").density == "spacious"
    clear_preferences()


def test_preference_store_default_when_missing():
    clear_preferences()
    p = get_preferences("nobody")
    assert p == UIPreference()
    clear_preferences()


# ---------------------------------------------------------------------------
# Preference API endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preferences_get_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/admin/preferences")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_preferences_put_requires_auth(client: AsyncClient):
    resp = await client.put("/api/v1/admin/preferences", json={"density": "compact"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_preferences_get_returns_defaults(client: AsyncClient, superadmin):
    clear_preferences()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/admin/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["density"] == "comfortable"
    assert data["visible_columns"] == {}
    clear_preferences()


@pytest.mark.asyncio
async def test_preferences_put_updates(client: AsyncClient, superadmin):
    clear_preferences()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    resp = await client.put(
        "/api/v1/admin/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "density": "compact",
            "visible_columns": {"user": ["email", "full_name"]},
            "sorting": {},
            "navigation_favorites": [],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["density"] == "compact"
    clear_preferences()


@pytest.mark.asyncio
async def test_preferences_persist_across_requests(client: AsyncClient, superadmin):
    clear_preferences()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        "/api/v1/admin/preferences",
        headers=headers,
        json={"density": "spacious", "visible_columns": {}, "sorting": {}, "navigation_favorites": []},
    )
    resp = await client.get("/api/v1/admin/preferences", headers=headers)
    assert resp.json()["density"] == "spacious"
    clear_preferences()
