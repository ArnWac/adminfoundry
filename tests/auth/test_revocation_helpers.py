"""Branch coverage for the revocation helpers (Roadmap 3.2).

The provider/logout happy paths are exercised in
``test_revocation_provider_path.py``; this file pins the cheap guard
branches those flows skip — empty ``jti`` short-circuits, idempotent
re-revocation, and the ``exp``-claim parsing edge cases — so a regression
that (say) starts treating an empty jti as revoked fails loudly.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from asterion.auth.revocation import (
    is_token_revoked,
    revoke_token,
    token_exp_as_datetime,
)
from asterion.models.base import GLOBAL_METADATA


@pytest_asyncio.fixture
async def session():
    # GLOBAL_METADATA tables carry the ``public`` schema; map it away so the
    # DDL is valid on schema-less SQLite.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        execution_options={"schema_translate_map": {"public": None}},
    )
    async with engine.begin() as conn:
        await conn.run_sync(GLOBAL_METADATA.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


# --- empty-jti guards (no DB hit) ---


async def test_is_token_revoked_empty_jti_is_false(session):
    # Empty jti returns before any query — the decode step already
    # rejects tokens without a jti.
    assert await is_token_revoked(session, "") is False


async def test_revoke_token_empty_jti_is_noop(session):
    assert await revoke_token(session, jti="") is False


# --- idempotency ---


async def test_revoke_token_is_idempotent(session):
    first = await revoke_token(session, jti="jti-abc", reason="logout")
    assert first is True
    assert await is_token_revoked(session, "jti-abc") is True
    # Revoking the same jti again is a no-op.
    second = await revoke_token(session, jti="jti-abc")
    assert second is False


# --- token_exp_as_datetime (pure) ---


def test_token_exp_as_datetime_valid():
    ts = 1_700_000_000
    result = token_exp_as_datetime({"exp": ts})
    assert result == datetime.fromtimestamp(ts, tz=UTC)


def test_token_exp_as_datetime_missing_claim_is_none():
    assert token_exp_as_datetime({}) is None


@pytest.mark.parametrize("bad_exp", ["not-a-number", [1, 2], {"nested": 1}])
def test_token_exp_as_datetime_malformed_is_none(bad_exp):
    # Non-numeric / out-of-range exp must degrade to None rather than
    # raising — the revocation row simply won't carry an expiry hint.
    assert token_exp_as_datetime({"exp": bad_exp}) is None
