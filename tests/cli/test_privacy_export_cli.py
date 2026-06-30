"""CLI tests for ``asterion privacy export-subject`` (G8)."""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from typer.testing import CliRunner

from asterion.auth.password import hash_password
from asterion.cli.main import app as cli_app
from asterion.models.base import GlobalModel
from asterion.models.user import User


@pytest.fixture
def env(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'export-cli.db'}"
    monkeypatch.setenv("ASTERION_DATABASE_URL", url)
    monkeypatch.setenv("ASTERION_SECRET_KEY", "test-export-cli-secret")
    monkeypatch.setenv("ASTERION_ENABLE_MULTI_TENANT", "false")
    monkeypatch.setenv("ASTERION_ENABLE_BUILTIN_UI", "false")

    state: dict = {}

    async def _setup():
        engine = create_async_engine(
            url, execution_options={"schema_translate_map": {"public": None}}
        )
        async with engine.begin() as conn:
            await conn.run_sync(GlobalModel.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            async with session.begin():
                user = User(
                    email="subject@example.com",
                    hashed_password=hash_password("hunter2-strong"),
                    full_name="Subject",
                )
                session.add(user)
                await session.flush()
                state["uid"] = str(user.id)
        await engine.dispose()

    asyncio.run(_setup())
    return state


def test_export_subject_writes_bundle(env, tmp_path):
    out = tmp_path / "subject.json"
    result = CliRunner().invoke(
        cli_app, ["privacy", "export-subject", env["uid"], "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert bundle["subject"]["email"] == "subject@example.com"
    assert "hashed_password" not in bundle["subject"]


def test_export_subject_invalid_uuid_errors(env, tmp_path):
    out = tmp_path / "x.json"
    result = CliRunner().invoke(
        cli_app, ["privacy", "export-subject", "not-a-uuid", "--out", str(out)]
    )
    assert result.exit_code == 2
    assert not out.exists()


def test_export_subject_unknown_user_errors(env, tmp_path):
    out = tmp_path / "x.json"
    result = CliRunner().invoke(
        cli_app, ["privacy", "export-subject", str(uuid.uuid4()), "--out", str(out)]
    )
    assert result.exit_code == 2
    assert not out.exists()
