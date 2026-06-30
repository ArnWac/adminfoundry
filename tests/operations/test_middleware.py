"""Tests for RequestIDMiddleware + SecurityHeadersMiddleware."""

from __future__ import annotations

import pytest
from fastapi import Request  # imported at module level so FastAPI's
from fastapi.testclient import TestClient  # forward-ref resolver finds it

from asterion import CoreAdminConfig, create_admin
from asterion.core.middleware import REQUEST_ID_HEADER


@pytest.fixture
def app(tmp_path):
    return create_admin(
        config=CoreAdminConfig(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'mw.db'}",
            secret_key="test-mw-secret",
            enable_multi_tenant=False,
            enable_builtin_ui=False,
            enable_builtin_admins=False,
        )
    )


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# --- request id ---


def test_response_carries_generated_request_id(client):
    resp = client.get("/healthz")
    rid = resp.headers.get(REQUEST_ID_HEADER)
    assert rid
    assert len(rid) >= 16


def test_response_echoes_inbound_request_id(client):
    resp = client.get("/healthz", headers={REQUEST_ID_HEADER: "abc-123"})
    assert resp.headers[REQUEST_ID_HEADER] == "abc-123"


def test_each_request_gets_unique_id_when_unset(client):
    a = client.get("/healthz").headers[REQUEST_ID_HEADER]
    b = client.get("/healthz").headers[REQUEST_ID_HEADER]
    assert a != b


def test_request_id_available_on_request_state(app):
    """Add a probe route that reads request.state.request_id."""

    @app.get("/probe-request-id")
    async def probe(request: Request):
        return {"rid": request.state.request_id}

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/probe-request-id", headers={REQUEST_ID_HEADER: "xyz"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["rid"] == "xyz"


# --- security headers ---


def test_security_headers_present_by_default(client):
    resp = client.get("/healthz")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert resp.headers["X-Frame-Options"] == "DENY"


def test_security_headers_disabled_when_config_off(tmp_path):
    app = create_admin(
        config=CoreAdminConfig(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'no-sec.db'}",
            secret_key="test-no-sec",
            enable_multi_tenant=False,
            enable_builtin_ui=False,
            enable_builtin_admins=False,
            security_headers_enabled=False,
        )
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/healthz")
    assert "X-Content-Type-Options" not in resp.headers


# --- CSP (Review R14) ---


def test_no_csp_header_by_default(client):
    # The bundled UI uses inline scripts; no CSP is emitted unless configured.
    resp = client.get("/healthz")
    assert "Content-Security-Policy" not in resp.headers


def test_csp_header_emitted_when_configured(tmp_path):
    policy = "default-src 'self'; frame-ancestors 'none'"
    app = create_admin(
        config=CoreAdminConfig(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'csp.db'}",
            secret_key="test-csp",
            enable_multi_tenant=False,
            enable_builtin_ui=False,
            enable_builtin_admins=False,
            content_security_policy=policy,
        )
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/healthz")
    assert resp.headers["Content-Security-Policy"] == policy


# --- CSP nonce (G10) ---


def _nonce_app(tmp_path, policy):
    return create_admin(
        config=CoreAdminConfig(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'nonce.db'}",
            secret_key="test-nonce",
            enable_multi_tenant=False,
            enable_builtin_ui=False,
            enable_builtin_admins=False,
            content_security_policy=policy,
        )
    )


def test_csp_nonce_substituted_when_placeholder_present(tmp_path):
    policy = "default-src 'self'; script-src 'self' 'nonce-{nonce}'"
    app = _nonce_app(tmp_path, policy)
    with TestClient(app, raise_server_exceptions=False) as c:
        header = c.get("/healthz").headers["Content-Security-Policy"]
    # The literal placeholder is gone, replaced by a concrete nonce value.
    assert "{nonce}" not in header
    assert "'nonce-" in header
    # And the nonce is non-trivial (base64url of 16 bytes ~ 22 chars).
    nonce = header.split("'nonce-", 1)[1].split("'", 1)[0]
    assert len(nonce) >= 16


def test_csp_nonce_is_unique_per_request(tmp_path):
    policy = "script-src 'self' 'nonce-{nonce}'"
    app = _nonce_app(tmp_path, policy)
    with TestClient(app, raise_server_exceptions=False) as c:
        a = c.get("/healthz").headers["Content-Security-Policy"]
        b = c.get("/healthz").headers["Content-Security-Policy"]
    assert a != b  # fresh nonce each request


def _ui_csp_app(tmp_path, policy):
    return create_admin(
        config=CoreAdminConfig(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'uicsp.db'}",
            secret_key="test-uicsp",
            enable_multi_tenant=False,
            enable_builtin_admins=False,
            # Bundled UI ON — the warning path only applies here.
            content_security_policy=policy,
        )
    )


def test_warns_when_ui_csp_has_no_nonce(tmp_path, caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="asterion"):
        _ui_csp_app(tmp_path, "default-src 'self'")
    assert any("nonce placeholder" in r.message for r in caplog.records)


def test_no_warning_when_ui_csp_uses_nonce(tmp_path, caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="asterion"):
        _ui_csp_app(tmp_path, "script-src 'self' 'nonce-{nonce}'")
    assert not any("nonce placeholder" in r.message for r in caplog.records)
