"""Protocol-level spec for context assembly.

The default :func:`adminfoundry.admin.context.build_admin_context`
function already plays this role — it composes the four sub-providers
(:class:`AuthProvider`, :class:`UserProvider`, :class:`PermissionProvider`,
:class:`TenantProvider`) into an :class:`AdminContext`. Most apps never
need to replace the whole assembly; they just swap one of the four
sub-providers and the function does the right thing automatically.

The protocol exists for the rare case where an app wants to **replace
the entire context-construction step** — e.g. an apps with a
non-standard session model that doesn't fit the four-provider shape, or
a test harness that wants to hand-build the context without invoking any
provider.

This is a v1 documentation-level contract. The framework does not
currently accept an :class:`AdminContextProvider` instance via
``create_admin`` — that hook lands when (and if) a concrete external
provider needs it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fastapi import Request

from adminfoundry.admin.context import AdminContext


@runtime_checkable
class AdminContextProvider(Protocol):
    """Builds the request-scoped :class:`AdminContext`.

    Implementations may return an anonymous context (``principal=None``)
    for unauthenticated requests; raising 401 is a route-level decision.
    """

    async def from_request(self, request: Request) -> AdminContext: ...
