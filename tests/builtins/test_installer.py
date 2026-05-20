"""Tests for builtin admin installer."""

from __future__ import annotations

from adminfoundry.builtins.installer import install_builtin_admins
from adminfoundry.registry import AdminRegistry


def test_install_registers_tenant_role_admins():
    registry = AdminRegistry()
    install_builtin_admins(registry)
    names = registry.model_names()
    assert "tenant_roles" in names
    assert "tenant_role_permissions" in names
    assert "tenant_membership_roles" in names


def test_install_skips_already_registered():
    registry = AdminRegistry()
    install_builtin_admins(registry)
    install_builtin_admins(registry)  # second call should not raise
    assert registry.model_names().count("tenant_roles") == 1


def test_install_with_extra_admin():
    from adminfoundry.registry import ModelAdmin

    class _FakeModel:
        __tablename__ = "custom_things"

    class CustomAdmin(ModelAdmin):
        model = _FakeModel

    registry = AdminRegistry()
    install_builtin_admins(registry, extra_admins=(CustomAdmin,))
    assert "custom_things" in registry.model_names()


def test_skip_tenant_admins():
    registry = AdminRegistry()
    install_builtin_admins(registry, include_tenant_admins=False)
    assert registry.model_names() == []
