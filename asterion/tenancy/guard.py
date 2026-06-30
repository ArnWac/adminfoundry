"""Defense-in-depth guard for tenant-scoped writes (review item K3).

Tenant isolation rests entirely on the connection's ``search_path`` (see
[tenancy.md]). A tenant-scoped write that runs while ``search_path`` still
points at ``public`` (a forgotten ``SET LOCAL search_path``) would silently
land in — or read from — the wrong schema. That is the most expensive failure
mode in a schema-per-tenant design and produces no error on its own.

:func:`assert_tenant_search_path` is a cheap pre-write assertion that turns that
silent corruption into a loud failure. It is PostgreSQL-only: SQLite has no
schemas, so it is a no-op there (and SQLite never proves isolation anyway).

This is the small, interim guard the roadmap's G15 (PostgreSQL Row Level
Security) entry contemplates as a stronger second layer — it does not replace
the ``search_path`` mechanism, it just refuses to write blindly past it.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

#: search_path first-entries that mean "not inside a tenant schema".
_NON_TENANT_SCHEMAS = frozenset({"", "public", "$user", "pg_catalog"})


class TenantScopeError(RuntimeError):
    """Raised when a tenant-scoped write runs without a tenant ``search_path``."""


async def assert_tenant_search_path(session: AsyncSession) -> None:
    """Refuse a tenant-scoped write when ``search_path`` is public/unset.

    No-op on non-PostgreSQL backends. On PostgreSQL, reads the live
    ``search_path`` and raises :class:`TenantScopeError` when its first entry is
    not a tenant schema, so a misconfigured request fails loudly instead of
    writing into the wrong tenant's schema.
    """
    bind = session.bind
    if bind is None or bind.dialect.name != "postgresql":
        return
    raw = (await session.execute(text("SELECT current_setting('search_path', true)"))).scalar()
    first = (raw or "").split(",")[0].strip().strip('"')
    if first in _NON_TENANT_SCHEMAS:
        raise TenantScopeError(
            "Tenant-scoped write attempted without a tenant search_path "
            f"(current: {raw!r}). Refusing to write into the wrong schema."
        )
