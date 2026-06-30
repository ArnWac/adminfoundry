"""G2 — user anonymisation (DSGVO Art. 17 stage 2)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from asterion.auth.password import hash_password, verify_password
from asterion.db.session import DatabaseManager
from asterion.models.audit_log import AuditLog
from asterion.models.base import GlobalModel
from asterion.models.user import User
from asterion.privacy.anonymizer import (
    ANONYMIZED_EMAIL_DOMAIN,
    anonymize_audit_actor,
    anonymize_user,
    anonymized_email,
)


def test_anonymize_user_tombstones_all_pii():
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email="alice@example.com",
        hashed_password=hash_password("hunter2-strong"),
        full_name="Alice Example",
        is_active=True,
        totp_secret="ABC123",
        totp_enabled=True,
        token_version=3,
    )

    summary = anonymize_user(user)

    # PII gone, deterministic unroutable tombstone, uniqueness preserved.
    assert user.email == anonymized_email(uid)
    assert ANONYMIZED_EMAIL_DOMAIN in user.email
    assert user.full_name is None
    assert user.totp_secret is None
    assert user.totp_enabled is False
    # Login can never succeed: deactivated, token bumped, password unknowable.
    assert user.is_active is False
    assert user.token_version == 4
    assert verify_password("hunter2-strong", user.hashed_password) is False
    # Summary carries no PII.
    assert summary == {"user_id": str(uid), "anonymized": True}


def test_anonymized_email_is_unique_per_user():
    a, b = uuid.uuid4(), uuid.uuid4()
    assert anonymized_email(a) != anonymized_email(b)


@pytest.fixture
async def session(tmp_path):
    # DatabaseManager wires the SQLite ``public`` schema that GlobalModel tables
    # (AuditLog) qualify against; a bare engine raises "unknown database public".
    manager = DatabaseManager(f"sqlite+aiosqlite:///{tmp_path / 'anon.db'}")
    async with manager.engine.begin() as conn:
        await conn.run_sync(GlobalModel.metadata.create_all)
    factory = async_sessionmaker(manager.engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await manager.dispose()


async def test_anonymize_audit_actor_nulls_pii_keeps_row(session):
    actor = uuid.uuid4()
    other = uuid.uuid4()
    session.add_all(
        [
            AuditLog(
                method="POST",
                path="/x",
                status_code=200,
                action="login_success",
                actor_user_id=actor,
                actor_label="alice@example.com",
                ip_address="203.0.113.7",
            ),
            AuditLog(
                method="POST",
                path="/y",
                status_code=200,
                action="login_success",
                actor_user_id=other,
                actor_label="bob@example.com",
                ip_address="203.0.113.9",
            ),
        ]
    )
    await session.flush()

    touched = await anonymize_audit_actor(session, actor)
    assert touched == 1

    rows = (await session.execute(select(AuditLog))).scalars().all()
    by_actor = {r.actor_user_id: r for r in rows}
    # The actor's PII is nulled, but the row (action + actor_user_id) survives.
    assert by_actor[actor].actor_label is None
    assert by_actor[actor].ip_address is None
    assert by_actor[actor].action == "login_success"
    # Other actors are untouched.
    assert by_actor[other].actor_label == "bob@example.com"
    assert by_actor[other].ip_address == "203.0.113.9"
