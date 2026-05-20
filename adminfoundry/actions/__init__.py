"""Admin action descriptors and the canonical BulkDeleteAction.

Subclass :class:`AdminAction` and add the instance to ``ModelAdmin.actions``
to expose a custom action at ``POST /api/v1/admin/{resource}/_actions/{action_name}``.

Actions must use ``session.flush()`` to materialize changes. The request
session's transaction is committed by ``get_async_session`` after the action
returns successfully, so calling ``commit()`` inside an action would
short-circuit the request's transaction lifecycle.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class AdminAction:
    """Base class for an admin action.

    Subclasses set ``name``, ``label`` and implement ``execute``.
    """

    name: str = ""
    label: str = ""

    async def execute(
        self,
        records: list[Any],
        session: AsyncSession,
        user: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError(f"Action {self.name!r} has no execute() implementation")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "label": self.label}


class BulkDeleteAction(AdminAction):
    name = "delete"
    label = "Delete selected"

    async def execute(
        self,
        records: list[Any],
        session: AsyncSession,
        user: Any,
    ) -> dict[str, Any]:
        for record in records:
            await session.delete(record)
        await session.flush()
        return {
            "summary": f"Deleted {len(records)} record(s)",
            "affected": len(records),
        }


__all__ = [
    "AdminAction",
    "BulkDeleteAction",
]
