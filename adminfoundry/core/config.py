"""Typed configuration model for the adminfoundry framework.

Runtime code should consume CoreAdminConfig, not raw environment variables.
Use CoreAdminConfig.from_settings(settings) to build from the env-backed Settings object.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from adminfoundry.auth_provider import AuthProvider


@dataclass
class CoreAdminConfig:
    """Central typed configuration for an adminfoundry installation.

    Defaults produce a minimal core installation — optional extensions are off.
    Disabled features do not mount routers, expose metadata, or import heavy deps.

    Package-user example (no env vars required)::

        config = CoreAdminConfig(
            database_url="sqlite+aiosqlite:///./app.db",
            secret_key="my-secret",
            enable_multi_tenant=False,
        )
        app = create_admin(config=config, title="My Admin")

    Env-backed convenience::

        config = CoreAdminConfig.from_env(enable_multi_tenant=True, tenant_resolution="subdomain")
        app = create_admin(config=config, title="My SaaS Admin")
    """

    # Database — if set, create_admin() configures the engine from this URL.
    # When None the engine is lazily initialised from DATABASE_URL env / settings.
    database_url: str | None = None
    # JWT secret — if set, overrides SECRET_KEY env / settings for token signing.
    secret_key: str | None = None

    # Core features
    enable_builtin_ui: bool = True
    enable_multi_tenant: bool = False
    # "header" uses X-Tenant-Slug; "subdomain" extracts from the first hostname segment
    tenant_resolution: str = "header"

    # Locale defaults — applied as the initial value for all users who have
    # not yet saved a personal preference. Users can override in Settings.
    # language: BCP 47 tag, e.g. "en", "de", "fr"
    default_language: str = "en"
    # date_format: "locale" | "iso" | "eu" | "us" | "custom"
    default_date_format: str = "locale"
    default_date_pattern: str = "%Y-%m-%d %H:%M"
    default_show_timezone: bool = False

    # User-supplied extension instances (loaded in registration order)
    extensions: list[Any] = field(default_factory=list)

    # Optional custom auth provider — None uses the built-in JWT provider
    auth_provider: AuthProvider | None = None
    # Optional custom user model — must have id, email, is_active, is_superadmin.
    # adminfoundry validates the model against these requirements at startup.
    user_model: Any | None = None
    # Set False to skip mounting built-in login/logout/refresh routes
    include_auth_routes: bool = True

    # Cache backend URL — None uses in-process memory; "redis://..." uses Redis
    cache_backend: str | None = None

    # Storage backend instance — None uses LocalStorage("uploads")
    storage_backend: Any | None = None

    # Dashboard widgets — None uses DEFAULT_WIDGETS (core generic widgets only).
    # By default (mode "append"), user-supplied widgets are added after the core
    # defaults. Set dashboard_widgets_mode="replace" to fully replace DEFAULT_WIDGETS.
    # Widgets contributed by extensions are always appended after the base set.
    dashboard_widgets: list[Any] | None = None
    # "append" (default): user widgets added after DEFAULT_WIDGETS.
    # "replace": user widgets fully replace DEFAULT_WIDGETS.
    dashboard_widgets_mode: str = "append"

    # Extra i18n strings injected into the admin UI — merged on top of built-in strings.
    # Lets app code add/override translations without modifying the package.
    # Structure: {"en": {"my_action_label": "My Action"}, "de": {"my_action_label": "Meine Aktion"}}
    extra_i18n: dict = field(default_factory=dict)

    @classmethod
    def from_pyproject(cls, path: str | None = None) -> "CoreAdminConfig":
        """Build config from [tool.adminfoundry] in pyproject.toml (Python 3.11+ tomllib)."""
        import tomllib
        from pathlib import Path

        toml_path = Path(path) if path else Path("pyproject.toml")
        if not toml_path.exists():
            return cls()
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        s = data.get("tool", {}).get("adminfoundry", {})
        return cls(
            enable_builtin_ui=s.get("enable_builtin_ui", True),
            enable_multi_tenant=s.get("enable_multi_tenant", False),
            default_language=s.get("default_language", "en"),
            default_date_format=s.get("default_date_format", "locale"),
            default_date_pattern=s.get("default_date_pattern", "%Y-%m-%d %H:%M"),
            default_show_timezone=s.get("default_show_timezone", False),
        )

    @classmethod
    def from_settings(cls, settings: Any, **overrides) -> "CoreAdminConfig":
        """Build config from the env-backed Settings object.

        Precedence: explicit kwargs > settings object (env-backed) > built-in defaults.
        Explicit keyword overrides always win over values loaded from settings::

            config = CoreAdminConfig.from_settings(
                settings,
                enable_multi_tenant=True,
                tenant_resolution="subdomain",
                extensions=[WorkflowsExtension()],
            )
        """
        base: dict = dict(
            database_url=getattr(settings, "DATABASE_URL", None),
            secret_key=getattr(settings, "SECRET_KEY", None),
            enable_builtin_ui=getattr(settings, "ENABLE_BUILTIN_ADMIN_UI", True),
            enable_multi_tenant=getattr(settings, "MULTI_TENANT", False),
            tenant_resolution=getattr(settings, "TENANT_RESOLUTION_STRATEGY", "header"),
            auth_provider=None,
            include_auth_routes=True,
        )
        base.update(overrides)
        return cls(**base)

    @classmethod
    def from_env(cls, **overrides) -> "CoreAdminConfig":
        """Build config from environment variables; explicit kwargs always win.

        Reads DATABASE_URL, SECRET_KEY, MULTI_TENANT, TENANT_RESOLUTION_STRATEGY,
        and ENABLE_BUILTIN_ADMIN_UI from the environment (via pydantic-settings).
        Explicit overrides always take precedence::

            config = CoreAdminConfig.from_env(
                enable_multi_tenant=True,
                tenant_resolution="subdomain",
            )
        """
        from adminfoundry.settings import settings as _s
        return cls.from_settings(_s, **overrides)

    def enabled_extension_names(self) -> list[str]:
        """Return the names of all enabled user-provided extensions."""
        return [
            name
            for ext in self.extensions
            if (name := getattr(ext, "name", None))
        ]

    def to_safe_dict(self) -> dict:
        """UI-safe representation for admin contract and diagnostics. Never exposes secrets."""
        return {
            "enable_builtin_ui": self.enable_builtin_ui,
            "enable_multi_tenant": self.enable_multi_tenant,
            "tenant_resolution": self.tenant_resolution,
            "enabled_extensions": self.enabled_extension_names(),
            "database_url_set": self.database_url is not None,
            "secret_key_set": self.secret_key is not None,
        }
