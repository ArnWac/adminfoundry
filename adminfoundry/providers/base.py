"""Neutral provider protocols + DTOs.

Everything in this module is intentionally framework-agnostic — no
SQLAlchemy, no concrete model imports — so that external implementations
can be tiny adapters.

Phase 1 of the v1-providers refactor introduces these alongside the
existing code. Routers do not yet consume the protocols; the
:class:`~adminfoundry.admin.context.AdminContext` dependency does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from fastapi import Request

# ---------------------------------------------------------------------------
# DTOs — value objects passed between providers and the framework
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    """Identifies the authenticated principal.

    The framework treats ``user_id`` as opaque — it is whatever the
    :class:`UserProvider` will accept on ``get_by_id``. Built-in providers
    use the User's UUID as a string.

    ``claims`` carries any verified token payload (JWT claims, OAuth
    userinfo, session attributes) so downstream code can read them
    without knowing the auth mechanism.
    """

    user_id: str
    claims: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    """Neutral representation of an admin user.

    The full app-specific user object (whatever the UserProvider stores
    internally) does not leak across this boundary; AdminPrincipal is what
    every adminfoundry component sees.
    """

    id: str
    email: str | None = None
    display_name: str | None = None
    is_active: bool = True
    is_superadmin: bool = False


@dataclass(frozen=True, slots=True)
class AdminTenant:
    """Neutral representation of an active tenant.

    ``id`` is the opaque tenant identifier the TenantProvider works with.
    ``slug`` is the human-readable handle (also used by the built-in
    schema-per-tenant strategy as ``tenant_<slug>``).
    """

    id: str
    slug: str
    name: str | None = None


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class AuthProvider(Protocol):
    """Extracts an :class:`AuthIdentity` from a FastAPI request.

    Implementations are responsible for verifying credentials (JWT
    signature, OAuth token introspection, session lookup). Returning
    ``None`` means the request is anonymous; the framework then either
    rejects with 401 or treats the route as public, depending on the
    route's own dependencies.
    """

    async def authenticate_request(self, request: Request) -> AuthIdentity | None: ...


@runtime_checkable
class UserProvider(Protocol):
    """Loads an :class:`AdminPrincipal` from its opaque identifier.

    Returning ``None`` for a previously-authenticated ``user_id`` means
    the user has been deleted, deactivated, or hidden; the framework
    treats this as 401 / 403 the same way it would treat an invalid
    token.

    ``request`` is optional — external providers that hold their own
    backing store don't need it. Built-in providers use it to reach
    ``request.app.state.adminfoundry`` for DB access without storing
    framework references at construction time.
    """

    async def get_by_id(
        self,
        user_id: str,
        *,
        request: Request | None = None,
    ) -> AdminPrincipal | None: ...


@runtime_checkable
class PermissionProvider(Protocol):
    """Answers ``what is this user allowed to do`` questions.

    ``get_permissions`` returns the user's full set of granted permission
    keys for the given tenant context (or globally when ``tenant`` is
    None). Keys follow the existing ``admin.<resource>.<action>`` schema
    with ``*`` wildcards. The framework still uses
    :func:`adminfoundry.authz.permissions.has_permission` to match a
    required key against this set — the provider just produces the set.
    """

    def is_superadmin(self, user: AdminPrincipal) -> bool: ...

    async def get_permissions(
        self,
        user: AdminPrincipal,
        tenant: AdminTenant | None,
        *,
        request: Request | None = None,
    ) -> frozenset[str]: ...


@runtime_checkable
class TenantProvider(Protocol):
    """Resolves the active tenant from the request.

    Returns ``None`` for requests that target the public/root scope
    (root admin panel, login, etc.). The built-in provider reads the
    ``X-Tenant-Slug`` header or subdomain; external providers can pull
    from JWT claims, cookies, or anywhere else.
    """

    async def resolve_tenant(self, request: Request) -> AdminTenant | None: ...
