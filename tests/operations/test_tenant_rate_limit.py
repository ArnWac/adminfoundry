"""G19 — per-tenant request rate limiting (noisy-neighbour protection).

The middleware keys on the request's tenant slug (read from the header the same
way the resolver does), so it can be exercised without standing up real tenant
schemas: any path counts, and the limiter short-circuits with 429 before routing.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from asterion import CoreAdminConfig, create_admin

TENANT = {"X-Tenant-Slug": "acme"}
OTHER = {"X-Tenant-Slug": "beta"}


def _app(tmp_path, **overrides):
    return create_admin(
        config=CoreAdminConfig(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'trl.db'}",
            secret_key="test-trl-secret",
            enable_multi_tenant=False,
            enable_builtin_ui=False,
            enable_builtin_admins=False,
            **overrides,
        )
    )


def test_disabled_by_default_never_limits(tmp_path):
    app = _app(tmp_path)  # tenant_rate_limit_enabled defaults False
    with TestClient(app, raise_server_exceptions=False) as c:
        for _ in range(20):
            assert c.get("/healthz", headers=TENANT).status_code != 429


def test_enabled_limits_after_budget_exhausted(tmp_path):
    app = _app(
        tmp_path,
        tenant_rate_limit_enabled=True,
        tenant_rate_limit_max=3,
        tenant_rate_limit_window_seconds=60,
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        # First `max` tenant-scoped requests pass.
        for _ in range(3):
            assert c.get("/healthz", headers=TENANT).status_code != 429
        # The next is rejected with the rate_limited envelope.
        resp = c.get("/healthz", headers=TENANT)
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"]["code"] == "rate_limited"


def test_budget_is_per_tenant(tmp_path):
    app = _app(
        tmp_path,
        tenant_rate_limit_enabled=True,
        tenant_rate_limit_max=2,
        tenant_rate_limit_window_seconds=60,
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        # Exhaust tenant A.
        for _ in range(2):
            assert c.get("/healthz", headers=TENANT).status_code != 429
        assert c.get("/healthz", headers=TENANT).status_code == 429
        # Tenant B has its own, untouched budget.
        assert c.get("/healthz", headers=OTHER).status_code != 429
        assert c.get("/healthz", headers=OTHER).status_code != 429
        assert c.get("/healthz", headers=OTHER).status_code == 429


def test_requests_without_tenant_are_not_limited(tmp_path):
    app = _app(
        tmp_path,
        tenant_rate_limit_enabled=True,
        tenant_rate_limit_max=2,
        tenant_rate_limit_window_seconds=60,
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        # No tenant header → not subject to the per-tenant budget, ever.
        for _ in range(10):
            assert c.get("/healthz").status_code != 429
