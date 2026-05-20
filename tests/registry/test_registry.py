"""Tests for AdminRegistry."""

from __future__ import annotations

from adminfoundry.registry import AdminRegistry, ModelAdmin


class _FakeModel:
    __tablename__ = "fake_things"


class FakeAdmin(ModelAdmin):
    model = _FakeModel
    list_display = ["id"]


def test_register_and_get():
    registry = AdminRegistry()
    registry.register(FakeAdmin)
    result = registry.get("fake_things")
    assert result is not None
    assert isinstance(result, FakeAdmin)


def test_register_instance():
    registry = AdminRegistry()
    registry.register(FakeAdmin())
    assert registry.get("fake_things") is not None


def test_get_unknown_returns_none():
    registry = AdminRegistry()
    assert registry.get("nonexistent") is None


def test_all_returns_all():
    registry = AdminRegistry()
    registry.register(FakeAdmin)
    admins = registry.all()
    assert len(admins) == 1


def test_model_names():
    registry = AdminRegistry()
    registry.register(FakeAdmin)
    assert "fake_things" in registry.model_names()


def test_no_singleton():
    r1 = AdminRegistry()
    r2 = AdminRegistry()
    r1.register(FakeAdmin)
    assert r2.get("fake_things") is None


def test_is_registered():
    registry = AdminRegistry()
    assert not registry.is_registered(_FakeModel)
    registry.register(FakeAdmin)
    assert registry.is_registered(_FakeModel)
