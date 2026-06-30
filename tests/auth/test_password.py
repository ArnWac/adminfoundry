"""Tests for password hashing and verification."""

from __future__ import annotations

import bcrypt

from asterion.auth.password import (
    dummy_verify_password,
    hash_password,
    verify_password,
)


def test_hash_returns_non_empty_string():
    h = hash_password("my-password")
    assert isinstance(h, str)
    assert len(h) > 0


def test_hash_is_not_plaintext():
    h = hash_password("my-password")
    assert h != "my-password"


def test_verify_correct_password():
    h = hash_password("correct-horse")
    assert verify_password("correct-horse", h) is True


def test_verify_wrong_password():
    h = hash_password("correct-horse")
    assert verify_password("wrong-password", h) is False


def test_two_hashes_of_same_password_differ():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2


def test_empty_password_can_be_hashed():
    h = hash_password("")
    assert verify_password("", h) is True


def test_long_passwords_differing_after_72_bytes_do_not_collide():
    # Regression for the bcrypt 72-byte truncation: two passphrases that
    # share a 72-char prefix but differ afterwards must not verify against
    # each other. Pre-hashing with SHA-256 makes the whole input count.
    base = "A" * 72
    pw_a = base + "alpha-suffix"
    pw_b = base + "omega-suffix"
    h = hash_password(pw_a)
    assert verify_password(pw_a, h) is True
    assert verify_password(pw_b, h) is False


def test_legacy_truncated_hash_still_verifies():
    # Hashes minted before the pre-hash upgrade bcrypt'd the raw password.
    # verify_password must still accept them so existing logins survive.
    legacy_hash = bcrypt.hashpw(b"legacy-secret", bcrypt.gensalt()).decode()
    assert verify_password("legacy-secret", legacy_hash) is True
    assert verify_password("wrong", legacy_hash) is False


def test_dummy_verify_always_false():
    assert dummy_verify_password("anything") is False
