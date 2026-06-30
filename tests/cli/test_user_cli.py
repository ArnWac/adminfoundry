"""CLI smoke tests for ``asterion user ...`` commands (plan §PR-8)."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from typer.testing import CliRunner

from asterion.auth.password import hash_password, verify_password
from asterion.cli.main import app as cli_app
from asterion.models.base import GlobalModel
from asterion.models.user import User


@pytest.fixture
def env(tmp_path, monkeypatch):
    db_path = tmp_path / "user-cli.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    monkeypatch.setenv("ASTERION_DATABASE_URL", url)
    monkeypatch.setenv("ASTERION_SECRET_KEY", "test-user-cli-secret")
    monkeypatch.setenv("ASTERION_ENABLE_MULTI_TENANT", "false")
    monkeypatch.setenv("ASTERION_ENABLE_BUILTIN_UI", "false")

    async def _setup():
        engine = create_async_engine(
            url,
            execution_options={"schema_translate_map": {"public": None}},
        )
        async with engine.begin() as conn:
            await conn.run_sync(GlobalModel.metadata.create_all)
        await engine.dispose()

    asyncio.run(_setup())
    return url


def _engine_for(url: str):
    return create_async_engine(url, execution_options={"schema_translate_map": {"public": None}})


def _read_user(url: str, email: str) -> User | None:
    async def _go():
        engine = _engine_for(url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
        await engine.dispose()
        return user

    return asyncio.run(_go())


def _seed_user(url: str, **kw):
    async def _go():
        engine = _engine_for(url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            async with session.begin():
                user = User(
                    email=kw.get("email", "seed@example.com"),
                    hashed_password=hash_password(kw.get("password", "hunter2-strong")),
                    full_name=kw.get("full_name"),
                    is_active=kw.get("is_active", True),
                    is_superadmin=kw.get("is_superadmin", False),
                    token_version=kw.get("token_version", 0),
                )
                session.add(user)
            await session.refresh(user)
            return user

    return asyncio.run(_go())


def _runner() -> CliRunner:
    return CliRunner()


# --- create ---


def test_user_create_creates_user(env):
    result = _runner().invoke(
        cli_app,
        ["user", "create", "--email", "alice@example.com"],
        input="hunter2-strong\nhunter2-strong\n",
    )
    assert result.exit_code == 0, result.output
    user = _read_user(env, "alice@example.com")
    assert user is not None
    assert user.is_active is True
    assert user.is_superadmin is False
    assert verify_password("hunter2-strong", user.hashed_password)


def test_user_create_with_superadmin_flag(env):
    result = _runner().invoke(
        cli_app,
        [
            "user",
            "create",
            "--email",
            "root@example.com",
            "--full-name",
            "Root",
            "--superadmin",
        ],
        input="hunter2-strong\nhunter2-strong\n",
    )
    assert result.exit_code == 0
    user = _read_user(env, "root@example.com")
    assert user.is_superadmin is True
    assert user.full_name == "Root"


def test_user_create_rejects_duplicate_email(env):
    _seed_user(env, email="alice@example.com")
    result = _runner().invoke(
        cli_app,
        ["user", "create", "--email", "alice@example.com"],
        input="hunter2-strong\nhunter2-strong\n",
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


# --- list ---


def test_user_list_empty(env):
    result = _runner().invoke(cli_app, ["user", "list"])
    assert result.exit_code == 0
    assert "No users" in result.output


def test_user_list_shows_users(env):
    _seed_user(env, email="alice@example.com", full_name="Alice")
    _seed_user(env, email="bob@example.com", is_superadmin=True)

    result = _runner().invoke(cli_app, ["user", "list"])
    assert result.exit_code == 0
    assert "alice@example.com" in result.output
    assert "bob@example.com" in result.output


def test_user_list_search_filter(env):
    _seed_user(env, email="alice@example.com")
    _seed_user(env, email="bob@example.com")

    result = _runner().invoke(cli_app, ["user", "list", "--search", "alice"])
    assert "alice@example.com" in result.output
    assert "bob@example.com" not in result.output


def test_user_list_superadmin_filter(env):
    _seed_user(env, email="user@example.com", is_superadmin=False)
    _seed_user(env, email="root@example.com", is_superadmin=True)

    result = _runner().invoke(cli_app, ["user", "list", "--superadmin"])
    assert "root@example.com" in result.output
    assert "user@example.com" not in result.output


def test_user_list_inactive_filter(env):
    # Use email prefixes that aren't substrings of each other, so the
    # "not in output" check below can't false-pass when one matches.
    _seed_user(env, email="alive@example.com", is_active=True)
    _seed_user(env, email="banned@example.com", is_active=False)

    result = _runner().invoke(cli_app, ["user", "list", "--inactive"])
    assert "banned@example.com" in result.output
    assert "alive@example.com" not in result.output


# --- disable / enable ---


def test_user_disable_marks_inactive_and_bumps_token_version(env):
    _seed_user(env, email="alice@example.com", is_active=True, token_version=5)

    result = _runner().invoke(cli_app, ["user", "disable", "--email", "alice@example.com"])
    assert result.exit_code == 0
    user = _read_user(env, "alice@example.com")
    assert user.is_active is False
    assert user.token_version == 6  # bumped so existing tokens fail
    assert user.deactivated_at is not None  # G2 retention clock started


def test_user_enable_clears_deactivated_at(env):
    _seed_user(env, email="alice@example.com", is_active=True)
    _runner().invoke(cli_app, ["user", "disable", "--email", "alice@example.com"])
    assert _read_user(env, "alice@example.com").deactivated_at is not None

    result = _runner().invoke(cli_app, ["user", "enable", "--email", "alice@example.com"])
    assert result.exit_code == 0
    assert _read_user(env, "alice@example.com").deactivated_at is None


def test_user_disable_idempotent(env):
    _seed_user(env, email="alice@example.com", is_active=False, token_version=2)
    result = _runner().invoke(cli_app, ["user", "disable", "--email", "alice@example.com"])
    assert result.exit_code == 0
    assert "already disabled" in result.output
    user = _read_user(env, "alice@example.com")
    # token_version untouched on no-op
    assert user.token_version == 2


def test_user_enable_reactivates_without_bumping_tkv(env):
    _seed_user(env, email="alice@example.com", is_active=False, token_version=4)
    result = _runner().invoke(cli_app, ["user", "enable", "--email", "alice@example.com"])
    assert result.exit_code == 0
    user = _read_user(env, "alice@example.com")
    assert user.is_active is True
    assert user.token_version == 4


def test_user_disable_unknown_email(env):
    result = _runner().invoke(cli_app, ["user", "disable", "--email", "ghost@example.com"])
    assert result.exit_code != 0


def test_user_enable_unknown_email(env):
    result = _runner().invoke(cli_app, ["user", "enable", "--email", "ghost@example.com"])
    assert result.exit_code != 0


# --- anonymize (G2) ---


def _seed_audit_actor(url: str, actor_id, email: str):
    from asterion.models.audit_log import AuditLog

    async def _go():
        engine = _engine_for(url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            async with session.begin():
                session.add(
                    AuditLog(
                        method="POST",
                        path="/login",
                        status_code=200,
                        action="login_success",
                        actor_user_id=actor_id,
                        actor_label=email,
                        ip_address="203.0.113.5",
                    )
                )
        await engine.dispose()

    asyncio.run(_go())


def test_user_anonymize_tombstones_pii(env):
    user = _seed_user(env, email="alice@example.com", full_name="Alice", token_version=2)
    _seed_audit_actor(env, user.id, "alice@example.com")

    result = _runner().invoke(
        cli_app, ["user", "anonymize", "--email", "alice@example.com", "--yes"]
    )
    assert result.exit_code == 0, result.output

    # The original email is gone — read the tombstoned row by id.
    from asterion.privacy.anonymizer import anonymized_email

    fresh = _read_user(env, anonymized_email(user.id))
    assert fresh is not None
    assert fresh.full_name is None
    assert fresh.is_active is False
    assert fresh.token_version == 3
    assert verify_password("hunter2-strong", fresh.hashed_password) is False
    assert _read_user(env, "alice@example.com") is None


def test_user_anonymize_unknown_email(env):
    result = _runner().invoke(
        cli_app, ["user", "anonymize", "--email", "ghost@example.com", "--yes"]
    )
    assert result.exit_code != 0


def test_user_anonymize_aborts_without_confirmation(env):
    _seed_user(env, email="alice@example.com")
    result = _runner().invoke(
        cli_app, ["user", "anonymize", "--email", "alice@example.com"], input="n\n"
    )
    assert "Aborted" in result.output
    # Still present + unchanged.
    assert _read_user(env, "alice@example.com") is not None
