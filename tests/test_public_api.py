"""Smoke tests for the V1 public adminfoundry import surface.

V1 root API is intentionally minimal — actions/dashboards/signals/cache/storage/i18n
live under explicit submodule paths.
"""


def test_top_level_imports_resolve():
    from adminfoundry import (
        create_admin,
        CoreAdminConfig,
        ModelAdmin,
        admin_site,
        AuthProvider,
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


def test_actions_no_longer_in_root_api():
    """V1: actions are not re-exported from `adminfoundry` root."""
    import adminfoundry
    for name in (
        "BulkDeleteAction",
        "DeactivateUsersAction",
        "ActivateUsersAction",
        "DisableTenantAction",
        "EnableTenantAction",
        "DashboardWidget",
        "signals",
        "cache",
        "storage",
        "t",
    ):
        assert name not in adminfoundry.__all__, (
            f"{name} should not be in root __all__ in V1"
        )
