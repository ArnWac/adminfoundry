"""
Base class for admin bulk actions.

Usage::

    from adminfoundry.admin.actions import AdminAction

    class DeactivateAction(AdminAction):
        name = "deactivate"
        label = "Deactivate selected"
        danger = True
        confirm = True

        async def execute(self, objects, db, user):
            for obj in objects:
                obj.is_active = False
            await db.commit()
            return {"affected": len(objects)}
"""
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession


class AdminAction:
    name: str
    label: str
    danger: bool = False
    confirm: bool = False
    bulk: bool = True
    single: bool = True
    async_execution: bool = False

    async def execute(self, objects: list, db: AsyncSession, user: Any) -> dict:
        raise NotImplementedError(f"Action '{self.name}' has no execute() implementation")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "danger": self.danger,
            "confirm": self.confirm,
            "bulk": self.bulk,
            "single": self.single,
            "async_execution": self.async_execution,
        }
