"""Tests for the configurable DB pool plumbing."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from asterion import CoreAdminConfig
from asterion.db.session import DatabaseManager


def test_pool_kwargs_passed_to_postgres_engine():
    captured: dict = {}

    def _spy(url, **kw):
        captured["url"] = url
        captured.update(kw)
        # Return a real (lazy) async engine to satisfy DatabaseManager init
        from sqlalchemy.ext.asyncio import create_async_engine

        return create_async_engine(url, **kw)

    with patch("asterion.db.session.create_async_engine", side_effect=_spy):
        DatabaseManager(
            "postgresql+asyncpg://postgres:postgres@localhost:5432/x",
            pool_size=42,
            max_overflow=7,
            pool_pre_ping=False,
        )

    assert captured["pool_size"] == 42
    assert captured["max_overflow"] == 7
    assert captured["pool_pre_ping"] is False


def test_pool_kwargs_NOT_forwarded_for_sqlite():
    """SQLite uses NullPool / no pool_size. Forwarding pool_size would be
    silently ignored by SQLAlchemy but it should not be passed at all to
    keep the call explicit."""
    captured: dict = {}

    def _spy(url, **kw):
        captured["url"] = url
        captured.update(kw)
        from sqlalchemy.ext.asyncio import create_async_engine

        return create_async_engine(url, **kw)

    with patch("asterion.db.session.create_async_engine", side_effect=_spy):
        DatabaseManager(
            "sqlite+aiosqlite:///:memory:",
            pool_size=99,
            max_overflow=99,
        )

    assert "pool_size" not in captured
    assert "max_overflow" not in captured


def test_config_pool_fields_validate():
    with pytest.raises(ValueError, match="db_pool_size"):
        CoreAdminConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            secret_key="x" * 32,
            db_pool_size=0,
        ).validate()

    with pytest.raises(ValueError, match="db_max_overflow"):
        CoreAdminConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            secret_key="x" * 32,
            db_max_overflow=-1,
        ).validate()


def test_config_pool_defaults():
    cfg = CoreAdminConfig(
        database_url="sqlite+aiosqlite:///:memory:",
        secret_key="x" * 32,
    )
    assert cfg.db_pool_size == 10
    assert cfg.db_max_overflow == 20
    assert cfg.db_pool_pre_ping is True


# ---------------------------------------------------------------------------
# Statement-cache plumbing (v0.1.32): asyncpg's prepared-statement cache is
# incompatible with schema-per-tenant search_path switching on a shared pool.
# ---------------------------------------------------------------------------
def _capture_engine_kwargs(url: str, **manager_kw) -> dict:
    captured: dict = {}

    def _spy(spied_url, **kw):
        captured["url"] = spied_url
        captured.update(kw)
        from sqlalchemy.ext.asyncio import create_async_engine

        return create_async_engine(spied_url, **kw)

    with patch("asterion.db.session.create_async_engine", side_effect=_spy):
        DatabaseManager(url, **manager_kw)
    return captured


def test_statement_cache_size_zero_sets_asyncpg_connect_arg():
    captured = _capture_engine_kwargs(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/x",
        statement_cache_size=0,
    )
    assert captured["connect_args"] == {"statement_cache_size": 0}


def test_statement_cache_size_none_leaves_connect_args_unset():
    """None must not touch asyncpg's default cache (single-tenant speed-up)."""
    captured = _capture_engine_kwargs(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/x",
        statement_cache_size=None,
    )
    assert "connect_args" not in captured


def test_statement_cache_size_ignored_for_sqlite():
    captured = _capture_engine_kwargs(
        "sqlite+aiosqlite:///:memory:",
        statement_cache_size=0,
    )
    assert "connect_args" not in captured


def test_resolved_statement_cache_size_auto_disables_for_multi_tenant():
    cfg = CoreAdminConfig(
        database_url="postgresql+asyncpg://postgres:postgres@localhost/x",
        secret_key="x" * 32,
        enable_multi_tenant=True,
    )
    assert cfg.resolved_statement_cache_size() == 0


def test_resolved_statement_cache_size_auto_keeps_default_for_single_tenant():
    cfg = CoreAdminConfig(
        database_url="postgresql+asyncpg://postgres:postgres@localhost/x",
        secret_key="x" * 32,
        enable_multi_tenant=False,
    )
    assert cfg.resolved_statement_cache_size() is None


def test_resolved_statement_cache_size_explicit_override_wins():
    # Explicit value beats the multi-tenant auto-default either direction.
    cfg = CoreAdminConfig(
        database_url="postgresql+asyncpg://postgres:postgres@localhost/x",
        secret_key="x" * 32,
        enable_multi_tenant=True,
        db_statement_cache_size=50,
    )
    assert cfg.resolved_statement_cache_size() == 50


def test_config_rejects_negative_statement_cache_size():
    with pytest.raises(ValueError, match="db_statement_cache_size"):
        CoreAdminConfig(
            database_url="sqlite+aiosqlite:///:memory:",
            secret_key="x" * 32,
            db_statement_cache_size=-1,
        ).validate()
