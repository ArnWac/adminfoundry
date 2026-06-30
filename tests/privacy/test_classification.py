"""G1 — PII classification registry."""

from __future__ import annotations

import pytest

from asterion.privacy import (
    PIICategory,
    PIIFieldRegistry,
    get_pii_registry,
    reset_for_tests,
)
from asterion.privacy.classification import RegistryFrozenError


def test_default_seed_classifies_framework_pii():
    reg = PIIFieldRegistry()
    assert reg.category_of("email") is PIICategory.CONTACT
    assert reg.category_of("full_name") is PIICategory.IDENTITY
    # Audit-side PII is seeded so the future redactor can find it.
    assert reg.category_of("actor_label") is PIICategory.CONTACT
    assert reg.category_of("ip_address") is PIICategory.CONTACT


def test_unclassified_field_returns_none():
    reg = PIIFieldRegistry()
    assert reg.category_of("widget_count") is None
    assert "widget_count" not in reg
    assert reg.category_of(None) is None


def test_register_overwrites_to_tighten():
    reg = PIIFieldRegistry()
    reg.register("email", PIICategory.SENSITIVE)
    assert reg.category_of("email") is PIICategory.SENSITIVE


def test_register_rejects_bad_input():
    reg = PIIFieldRegistry()
    with pytest.raises(ValueError):
        reg.register("", PIICategory.IDENTITY)
    with pytest.raises(ValueError):
        reg.register("x", "identity")  # type: ignore[arg-type]


def test_freeze_blocks_further_registration():
    reg = PIIFieldRegistry()
    reg.freeze()
    assert reg.is_frozen is True
    with pytest.raises(RegistryFrozenError):
        reg.register("phone", PIICategory.CONTACT)


def test_names_in_filters_by_category():
    reg = PIIFieldRegistry(defaults={})
    reg.register_many(
        {
            "punch_time": PIICategory.BEHAVIORAL,
            "shift_note": PIICategory.BEHAVIORAL,
            "email": PIICategory.CONTACT,
        }
    )
    assert reg.names_in(PIICategory.BEHAVIORAL) == frozenset({"punch_time", "shift_note"})
    assert reg.names_in(PIICategory.CONTACT) == frozenset({"email"})


def test_singleton_and_reset():
    reset_for_tests()
    reg = get_pii_registry()
    assert reg.category_of("email") is PIICategory.CONTACT
    reg.register("home_address", PIICategory.CONTACT)
    assert "home_address" in get_pii_registry()
    # Reset restores a clean default seed.
    reset_for_tests()
    assert "home_address" not in get_pii_registry()


def test_reset_with_custom_defaults():
    reset_for_tests([("badge_id", PIICategory.IDENTITY)])
    reg = get_pii_registry()
    assert reg.category_of("badge_id") is PIICategory.IDENTITY
    assert reg.category_of("email") is None
    reset_for_tests()
