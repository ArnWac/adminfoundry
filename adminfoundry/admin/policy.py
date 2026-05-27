"""Central policy object: object- and resource-level access decisions.

A :class:`ModelAdmin` may set ``policy = MyPolicy()`` to layer
object-level / record-level rules on top of the existing
permission-key matcher. The framework runs both checks:

* permission key (``admin.<resource>.<action>``) — gates the route by
  the caller's grant set,
* policy method (``can_view_object`` / ``can_update_object`` /
  ``can_delete_object`` / ``can_view_model`` / ``can_create``,
  ``field_permission``) — gates the operation / individual field by
  app-defined rules (typically "the row's owner_id must equal the
  caller").

Both must allow for the operation to proceed. Defaults return permissive
values so an admin without a custom policy behaves exactly as before B3.

Policies are async because real-world checks often hit the DB ("does
this user share a team with the row's owner?"). Synchronous predicates
just ignore the ``async def`` ceremony — there's no cost.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from adminfoundry.admin.context import AdminContext


class FieldPermission(str, Enum):
    """How the current caller may interact with one field.

    * ``WRITE`` — full read + write access (the default).
    * ``READ`` — read access only; the field is omitted from the
      create/update schema and a payload that contains it is rejected
      by ``extra="forbid"``.
    * ``HIDDEN`` — the field is omitted everywhere — serialized
      output, contract, create/update schema. Treat as if the field
      didn't exist for this caller.

    Subclass values are ordered loosest → strictest. Inheriting from
    ``str`` keeps the enum JSON-serializable so the contract can ship
    the value directly.
    """

    WRITE = "write"
    READ = "read"
    HIDDEN = "hidden"


class AdminPolicy:
    """Default-allow policy. Subclass and override only the methods you
    want to constrain — every method has a permissive default.

    Method signatures intentionally mirror the planned future surface
    (``field_permission`` is per-field; ``record_filter`` for list
    scoping lands later). Adding new methods with safe defaults is
    backward-compatible.
    """

    async def can_view_model(self, ctx: "AdminContext") -> bool:
        """Gate the entire admin (list + read + write). Use for
        resource-level visibility ("hide the Orders admin from
        non-staff users entirely")."""
        return True

    async def can_create(self, ctx: "AdminContext") -> bool:
        """Per-resource create gate. Runs before payload validation —
        useful for "no new orders during freeze week" style rules."""
        return True

    async def can_view_object(self, obj: Any, ctx: "AdminContext") -> bool:
        """Per-object read gate. Runs after the row has been fetched,
        before the response is built."""
        return True

    async def can_update_object(self, obj: Any, ctx: "AdminContext") -> bool:
        """Per-object update gate. Runs after fetch, before
        ``validate_update`` / ``before_update``."""
        return True

    async def can_delete_object(self, obj: Any, ctx: "AdminContext") -> bool:
        """Per-object delete gate. Runs after fetch, before
        ``before_delete``."""
        return True

    async def field_permission(
        self,
        field: str,
        obj: Any,
        ctx: "AdminContext",
    ) -> FieldPermission:
        """Per-field decision for one caller.

        Returns :class:`FieldPermission`. Default is ``WRITE`` —
        every field is fully accessible. Override to hide or
        soft-readonly specific columns based on the caller's role or
        the object's state.

        ``obj`` is ``None`` on the create path (no row exists yet);
        policies that need the object should treat ``None`` as
        "first-time creation" and decide accordingly. The
        :class:`FieldPermission.HIDDEN` decision on create means
        "this field is invisible during creation" — the input is
        rejected and the field is missing from the form.
        """
        return FieldPermission.WRITE
