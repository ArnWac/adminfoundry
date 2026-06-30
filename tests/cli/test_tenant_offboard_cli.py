"""CLI tests for ``asterion tenant export`` / ``tenant offboard`` (G6)."""

from __future__ import annotations

import asyncio
import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from typer.testing import CliRunner

from asterion.auth.password import hash_password
from asterion.cli.main import app as cli_app
from asterion.models.base import GlobalModel
from asterion.models.tenant import Tenant
from asterion.models.tenant_membership import TenantMembership
from asterion.models.user import User


@pytest.fixture
def env(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'offboard-cli.db'}"
    monkeypatch.setenv("ASTERION_DATABASE_URL", url)
    monkeypatch.setenv("ASTERION_SECRET_KEY", "test-offboard-cli-secret")
    monkeypatch.setenv("ASTERION_ENABLE_MULTI_TENANT", "false")
    monkeypatch.setenv("ASTERION_ENABLE_BUILTIN_UI", "false")

    async def _setup():
        engine = _engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(GlobalModel.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            async with session.begin():
                user = User(
                    email="owner@example.com",
                    hashed_password=hash_password("hunter2-strong"),
                )
                tenant = Tenant(name="Acme", slug="acme", schema_name="tenant_acme")
                session.add_all([user, tenant])
                await session.flush()
                session.add(TenantMembership(user_id=user.id, tenant_id=tenant.id))
        await engine.dispose()

    asyncio.run(_setup())
    return url


def _engine(url):
    return create_async_engine(url, execution_options={"schema_translate_map": {"public": None}})


def _tenant_slugs(url):
    async def _go():
        engine = _engine(url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            slugs = [t.slug for t in (await session.execute(select(Tenant))).scalars().all()]
        await engine.dispose()
        return slugs

    return asyncio.run(_go())


def test_tenant_export_writes_bundle(env, tmp_path):
    out = tmp_path / "acme.json"
    result = CliRunner().invoke(cli_app, ["tenant", "export", "acme", "--out", str(out)])
    assert result.exit_code == 0, result.output
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert bundle["tenant"]["slug"] == "acme"
    assert len(bundle["memberships"]) == 1


def test_tenant_export_unknown_slug_errors(env, tmp_path):
    out = tmp_path / "ghost.json"
    result = CliRunner().invoke(cli_app, ["tenant", "export", "ghost", "--out", str(out)])
    assert result.exit_code == 2
    assert not out.exists()


def test_tenant_offboard_drop_removes_tenant(env, tmp_path):
    out = tmp_path / "bundle.json"
    result = CliRunner().invoke(
        cli_app,
        ["tenant", "offboard", "acme", "--mode", "drop", "--out", str(out), "--yes"],
    )
    assert result.exit_code == 0, result.output
    assert "Offboarded tenant 'acme'" in result.output
    assert out.exists()  # bundle persisted
    assert "acme" not in _tenant_slugs(env)


def test_tenant_offboard_archive_keeps_tenant(env):
    result = CliRunner().invoke(
        cli_app, ["tenant", "offboard", "acme", "--mode", "archive", "--yes"]
    )
    assert result.exit_code == 0, result.output
    # Tombstone row survives in archive mode.
    assert "acme" in _tenant_slugs(env)


def test_tenant_offboard_rejects_bad_mode(env):
    result = CliRunner().invoke(cli_app, ["tenant", "offboard", "acme", "--mode", "nuke", "--yes"])
    assert result.exit_code == 2
    assert "Invalid --mode" in result.output


def test_tenant_offboard_aborts_without_confirmation(env):
    result = CliRunner().invoke(cli_app, ["tenant", "offboard", "acme"], input="n\n")
    assert "Aborted" in result.output
    assert "acme" in _tenant_slugs(env)
