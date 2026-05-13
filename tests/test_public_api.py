"""Smoke tests for the public adminfoundry import surface."""


def test_top_level_imports_resolve():
    from adminfoundry import (
        create_admin,
        CoreAdminConfig,
        ModelAdmin,
        admin_site,
        AuthProvider,
        BulkDeleteAction,
        DeactivateUsersAction,
        ActivateUsersAction,
        DisableTenantAction,
        EnableTenantAction,
        __version__,
    )
    assert callable(create_admin)
    assert isinstance(__version__, str)


def test_actions_subpackage_resolves():
    from adminfoundry.actions import (
        BulkDeleteAction,
        DeactivateUsersAction,
        ActivateUsersAction,
        DisableTenantAction,
        EnableTenantAction,
    )
    # Each action has the required class attrs
    for cls in (
        BulkDeleteAction,
        DeactivateUsersAction,
        ActivateUsersAction,
        DisableTenantAction,
        EnableTenantAction,
    ):
        a = cls()
        assert isinstance(a.name, str) and a.name
        assert isinstance(a.label, str) and a.label
