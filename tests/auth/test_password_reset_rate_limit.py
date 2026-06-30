"""Rate-limiting of POST /auth/password-reset/request (review Point 1).

The reset endpoint always returns 202 (anti-enumeration). On top of that, a
per-email throttle caps how many reset emails/tokens a single address can
trigger before further requests get 429 — without revealing account existence
(every request is counted, existent or not).
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from asterion import CoreAdminConfig, create_admin
from asterion.auth.password import hash_password
from asterion.models.base import GlobalModel
from asterion.models.password_reset_token import PasswordResetToken
from asterion.models.user import User

SECRET = "test-reset-rl-secret"


class _CapturingNotifier:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_reset(self, *, email: str, token: str, request=None) -> None:
        self.sent.append({"email": email, "token": token})


@pytest.fixture
def app_with_user(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'reset-rl.db'}"
    notifier = _CapturingNotifier()
    app = create_admin(
        config=CoreAdminConfig(
            database_url=db_url,
            secret_key=SECRET,
            enable_multi_tenant=False,
            enable_builtin_ui=False,
            enable_builtin_admins=False,
            password_reset_rate_limit_max=3,
            password_reset_rate_limit_window_seconds=900,
        ),
        password_reset_notifier=notifier,
    )
    runtime = app.state.asterion

    async def _setup():
        async with runtime.db.engine.begin() as conn:
            await conn.run_sync(GlobalModel.metadata.create_all)
        factory = async_sessionmaker(runtime.db.engine, expire_on_commit=False)
        async with factory() as session:
            async with session.begin():
                session.add(
                    User(
                        email="alice@example.com",
                        hashed_password=hash_password("old-password-123"),
                        is_active=True,
                    )
                )

    asyncio.run(_setup())
    yield app, runtime, notifier
    asyncio.run(runtime.db.dispose())


def _request(app, email: str):
    return TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/auth/password-reset/request", json={"email": email}
    )


def _count(runtime, model) -> int:
    async def _go():
        factory = async_sessionmaker(runtime.db.engine, expire_on_commit=False)
        async with factory() as session:
            return len((await session.execute(select(model))).scalars().all())

    return asyncio.run(_go())


def test_known_user_throttled_after_max(app_with_user):
    app, runtime, notifier = app_with_user
    # First 3 (the configured max) pass with 202 and issue a token each.
    for _ in range(3):
        assert _request(app, "alice@example.com").status_code == 202
    # The 4th is throttled.
    resp = _request(app, "alice@example.com")
    assert resp.status_code == 429
    # No extra token/email was produced by the throttled request.
    assert len(notifier.sent) == 3
    assert _count(runtime, PasswordResetToken) == 3


def test_throttle_does_not_leak_existence(app_with_user):
    app, _, _ = app_with_user
    # An unknown email is counted the same way: it also 429s after the max,
    # so the throttle response is identical to the known-user path.
    for _ in range(3):
        assert _request(app, "ghost@example.com").status_code == 202
    assert _request(app, "ghost@example.com").status_code == 429


def test_separate_emails_have_independent_counters(app_with_user):
    app, _, _ = app_with_user
    for _ in range(3):
        assert _request(app, "alice@example.com").status_code == 202
    # A different address still has its full budget.
    assert _request(app, "bob@example.com").status_code == 202
