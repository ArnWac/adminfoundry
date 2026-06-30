"""CLI tests for ``asterion privacy retention-run`` (G2/G3)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from typer.testing import CliRunner

from asterion.auth.password import hash_password
from asterion.cli.main import app as cli_app
from asterion.models.base import GlobalModel
from asterion.models.user import User


@pytest.fixture
def env(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'privacy-cli.db'}"
    monkeypatch.setenv("ASTERION_DATABASE_URL", url)
    monkeypatch.setenv("ASTERION_SECRET_KEY", "test-privacy-cli-secret")
    monkeypatch.setenv("ASTERION_ENABLE_MULTI_TENANT", "false")
    monkeypatch.setenv("ASTERION_ENABLE_BUILTIN_UI", "false")
    monkeypatch.setenv("ASTERION_AUDIT_RETENTION_DAYS", "90")

    async def _setup():
        engine = create_async_engine(
            url, execution_options={"schema_translate_map": {"public": None}}
        )
        async with engine.begin() as conn:
            await conn.run_sync(GlobalModel.metadata.create_all)
        await engine.dispose()

    asyncio.run(_setup())
    return url


def _engine(url):
    return create_async_engine(url, execution_options={"schema_translate_map": {"public": None}})


def _seed_deactivated(url, *, email, days_ago):
    async def _go():
        engine = _engine(url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            async with session.begin():
                session.add(
                    User(
                        email=email,
                        hashed_password=hash_password("hunter2-strong"),
                        is_active=False,
                        deactivated_at=datetime.now(UTC) - timedelta(days=days_ago),
                    )
                )
        await engine.dispose()

    asyncio.run(_go())


def _user_emails(url):
    async def _go():
        engine = _engine(url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            rows = (await session.execute(select(User))).scalars().all()
            emails = [r.email for r in rows]
        await engine.dispose()
        return emails

    return asyncio.run(_go())


def test_retention_run_anonymizes_expired_users(env, monkeypatch):
    monkeypatch.setenv("ASTERION_USER_ANONYMIZE_AFTER_DAYS", "180")
    _seed_deactivated(env, email="gone@example.com", days_ago=200)

    result = CliRunner().invoke(cli_app, ["privacy", "retention-run", "--yes"])
    assert result.exit_code == 0, result.output
    assert "anonymised 1 user" in result.output

    emails = _user_emails(env)
    assert "gone@example.com" not in emails
    assert any(e.endswith("@anonymized.invalid") for e in emails)


def test_retention_run_without_sperrfrist_leaves_users(env):
    # ASTERION_USER_ANONYMIZE_AFTER_DAYS unset → no anonymisation.
    _seed_deactivated(env, email="gone@example.com", days_ago=200)
    result = CliRunner().invoke(cli_app, ["privacy", "retention-run", "--yes"])
    assert result.exit_code == 0, result.output
    assert "anonymised 0 user" in result.output
    assert "gone@example.com" in _user_emails(env)


def test_retention_run_aborts_without_confirmation(env):
    result = CliRunner().invoke(cli_app, ["privacy", "retention-run"], input="n\n")
    assert "Aborted" in result.output
