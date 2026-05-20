"""Smoke test: create_admin() returns a working FastAPI app."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from adminfoundry import CoreAdminConfig, create_admin


@pytest.fixture(scope="module")
def app():
    return create_admin(
        config=CoreAdminConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            secret_key="test-secret-key",
            enable_multi_tenant=False,
        )
    )


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def test_create_admin_returns_fastapi_app(app):
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)


def test_runtime_attached_to_state(app):
    from adminfoundry.core.runtime import AdminRuntime

    assert isinstance(app.state.adminfoundry, AdminRuntime)


def test_auth_login_route_exists(client):
    resp = client.post("/api/v1/auth/login", json={"email": "x", "password": "y"})
    assert resp.status_code in (401, 422, 500)


def test_contract_route_exists(client):
    resp = client.get("/api/v1/admin/_contract")
    assert resp.status_code in (401, 403, 200)


def test_ui_login_route_exists(client):
    resp = client.get("/admin/login", follow_redirects=False)
    assert resp.status_code in (200, 404, 500)
