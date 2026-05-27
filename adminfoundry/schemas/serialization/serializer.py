"""Record serializer.

B4 makes the read path aware of :class:`AdminPolicy.field_permission`:
when a caller's policy returns ``HIDDEN`` for a field, that field is
omitted from the serialized output, regardless of ``protected_fields``.
``READ`` permission still serializes normally (it only constrains
writes).

The policy hook is opt-in via the ``ctx=`` argument. Without ``ctx`` the
serializer keeps the pre-B4 behaviour exactly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from adminfoundry.registry.admin import ModelAdmin

if TYPE_CHECKING:
    from adminfoundry.admin.context import AdminContext


def _serialize_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _calculated_value(fn, obj) -> Any:
    try:
        return _serialize_value(fn(obj))
    except Exception:
        return None


async def _hidden_fields_via_policy(
    obj: object,
    model_admin: ModelAdmin,
    ctx: "AdminContext | None",
) -> set[str]:
    """Compute the per-caller HIDDEN field set.

    Returns an empty set when no policy is attached or no ctx was
    supplied — preserves the pre-B4 wire format for legacy callers.
    """
    if ctx is None:
        return set()
    policy = getattr(model_admin, "policy", None)
    if policy is None:
        return set()
    from adminfoundry.admin.policy import FieldPermission

    hidden: set[str] = set()
    for col in obj.__table__.columns:  # type: ignore[attr-defined]
        perm = await policy.field_permission(col.name, obj, ctx)
        if perm is FieldPermission.HIDDEN:
            hidden.add(col.name)
    for fname in model_admin.calculated_fields:
        perm = await policy.field_permission(fname, obj, ctx)
        if perm is FieldPermission.HIDDEN:
            hidden.add(fname)
    return hidden


class Serializer:
    def serialize(
        self,
        obj: object,
        model_admin: ModelAdmin,
        *,
        hidden_extra: set[str] | None = None,
    ) -> dict:
        excluded = model_admin.all_protected
        if hidden_extra:
            excluded = excluded | frozenset(hidden_extra)
        result: dict = {}

        for col in obj.__table__.columns:  # type: ignore[attr-defined]
            if col.name in excluded:
                continue
            result[col.name] = _serialize_value(getattr(obj, col.name))

        for fname, fn in model_admin.calculated_fields.items():
            if fname in excluded:
                continue
            result[fname] = _calculated_value(fn, obj)

        return result

    def serialize_many(
        self,
        objs: list,
        model_admin: ModelAdmin,
        *,
        hidden_extra: set[str] | None = None,
    ) -> list[dict]:
        return [
            self.serialize(obj, model_admin, hidden_extra=hidden_extra) for obj in objs
        ]


serializer = Serializer()


def serialize_record(
    obj,
    model_admin: ModelAdmin,
    schema=None,
    *,
    hidden_extra: set[str] | None = None,
) -> dict:
    return serializer.serialize(obj, model_admin, hidden_extra=hidden_extra)


def serialize_records(
    objs: list,
    model_admin: ModelAdmin,
    *,
    hidden_extra: set[str] | None = None,
) -> list[dict]:
    return serializer.serialize_many(objs, model_admin, hidden_extra=hidden_extra)


async def serialize_record_with_policy(
    obj,
    model_admin: ModelAdmin,
    ctx: "AdminContext | None" = None,
) -> dict:
    """Convenience entry-point used by the CRUD service path.

    Computes the policy-driven HIDDEN field set once and delegates to
    :func:`serialize_record`. Sync callers that don't have a ctx (tests,
    background jobs) can stay on :func:`serialize_record` directly.
    """
    hidden = await _hidden_fields_via_policy(obj, model_admin, ctx)
    return serialize_record(obj, model_admin, hidden_extra=hidden)


async def serialize_records_with_policy(
    objs: list,
    model_admin: ModelAdmin,
    ctx: "AdminContext | None" = None,
) -> list[dict]:
    """List-equivalent of :func:`serialize_record_with_policy`.

    Computes the HIDDEN set against the first row only when at least
    one row is present. Per-row HIDDEN decisions are deliberately not
    supported here — that would require an N×K policy call and break
    the wire format ("some rows have field X, others don't"). Apps
    that want per-row hiding should use ``can_view_object`` on those
    rows instead.
    """
    if not objs:
        return []
    hidden = await _hidden_fields_via_policy(objs[0], model_admin, ctx)
    return serialize_records(objs, model_admin, hidden_extra=hidden)
