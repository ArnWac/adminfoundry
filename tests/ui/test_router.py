"""Smoke tests for the minimal built-in UI shell.

These verify that every route declared on /admin renders, that the static
asset mount serves admin.css/admin.js, and that the shell renders only the
two templates the plan permits (app.html, login.html). No real UI behavior
is exercised — the shell is intentionally minimal and is driven by the
contract + CRUD APIs at runtime via JavaScript.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adminfoundry import CoreAdminConfig, create_admin

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "adminfoundry"


@pytest.fixture
def app(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'ui.db'}"
    return create_admin(
        config=CoreAdminConfig(
            database_url=db_url,
            secret_key="test-ui-secret",
            enable_multi_tenant=False,
            enable_builtin_admins=False,
        )
    )


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# --- routes ---


def test_admin_root_redirects_to_dashboard(client):
    resp = client.get("/admin/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].endswith("/admin/dashboard")


def test_login_page_renders(client):
    resp = client.get("/admin/login")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert 'id="login-form"' in body
    assert "/api/v1/auth/login" not in body  # login URL is built in JS from cfg
    assert 'data-view="login"' in body


def test_dashboard_renders_shell(client):
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200
    assert 'data-view="dashboard"' in resp.text


def test_settings_renders_shell(client):
    resp = client.get("/admin/settings")
    assert resp.status_code == 200
    assert 'data-view="settings"' in resp.text


def test_resource_list_renders_shell(client):
    resp = client.get("/admin/widgets")
    assert resp.status_code == 200
    assert 'data-view="list"' in resp.text
    assert 'data-resource="widgets"' in resp.text


def test_resource_create_renders_shell(client):
    resp = client.get("/admin/widgets/new")
    assert resp.status_code == 200
    assert 'data-view="create"' in resp.text
    assert 'data-resource="widgets"' in resp.text


def test_resource_detail_renders_shell(client):
    resp = client.get("/admin/widgets/42")
    assert resp.status_code == 200
    assert 'data-view="detail"' in resp.text
    assert 'data-record-id="42"' in resp.text


def test_resource_edit_renders_shell(client):
    resp = client.get("/admin/widgets/42/edit")
    assert resp.status_code == 200
    assert 'data-view="edit"' in resp.text


def test_resource_delete_renders_shell(client):
    resp = client.get("/admin/widgets/42/delete")
    assert resp.status_code == 200
    assert 'data-view="delete"' in resp.text


# --- static asset mount ---


def test_static_css_served(client):
    resp = client.get("/admin/static/admin.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers["content-type"]


def test_static_js_served(client):
    resp = client.get("/admin/static/admin.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]


def test_static_unknown_returns_404(client):
    resp = client.get("/admin/static/nope.js")
    assert resp.status_code == 404


# --- template surface ---


def test_only_minimal_templates_exist():
    """Plan §Phase 4: 'They should only render: ui/templates/app.html,
    ui/templates/login.html'. Guards against legacy templates returning."""
    templates_dir = PACKAGE_ROOT / "ui" / "templates"
    files = sorted(p.name for p in templates_dir.iterdir() if p.is_file())
    assert files == ["app.html", "login.html"], files


def test_no_admin_subdirectory_left():
    templates_dir = PACKAGE_ROOT / "ui" / "templates"
    assert not (templates_dir / "admin").exists()


def test_no_legacy_static_assets():
    static_dir = PACKAGE_ROOT / "ui" / "static" / "admin"
    files = sorted(p.name for p in static_dir.iterdir() if p.is_file())
    assert files == ["admin.css", "admin.js"], files


# --- builtin UI can be disabled ---


def test_builtin_ui_disabled(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'ui-off.db'}"
    app = create_admin(
        config=CoreAdminConfig(
            database_url=db_url,
            secret_key="test-ui-off",
            enable_multi_tenant=False,
            enable_builtin_admins=False,
            enable_builtin_ui=False,
        )
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/admin/login")
    assert resp.status_code == 404
