"""
Common admin actions provided by the framework.

Import and attach to any ModelAdmin via the `actions` attribute::

    from adminfoundry.actions import BulkDeleteAction, DeactivateUsersAction

    class UserAdmin(ModelAdmin):
        actions = [DeactivateUsersAction(), BulkDeleteAction()]

All actions inherit from `adminfoundry.admin.actions.AdminAction` and follow the
standard execute(objects, db, user) -> dict contract.
"""
from adminfoundry.admin.actions import AdminAction


class BulkDeleteAction(AdminAction):
    name = "delete"
    label = "Delete selected"
    danger = True
    confirm = True
    bulk = True
    single = False

    async def execute(self, objects, db, user):
        count = len(objects)
        for obj in objects:
            await db.delete(obj)
        await db.commit()
        return {"summary": f"Deleted {count} record(s)", "affected": count}


class DeactivateUsersAction(AdminAction):
    name = "deactivate"
    label = "Deactivate selected"
    danger = True
    confirm = True
    bulk = True
    single = True

    async def execute(self, objects, db, user):
        for obj in objects:
            obj.is_active = False
        await db.commit()
        return {"summary": f"Deactivated {len(objects)} user(s)", "affected": len(objects)}


class ActivateUsersAction(AdminAction):
    name = "activate"
    label = "Activate selected"
    danger = False
    confirm = True
    bulk = True
    single = True

    async def execute(self, objects, db, user):
        for obj in objects:
            obj.is_active = True
        await db.commit()
        return {"summary": f"Activated {len(objects)} user(s)", "affected": len(objects)}


class DisableTenantAction(AdminAction):
    name = "disable"
    label = "Disable tenant"
    danger = True
    confirm = True
    bulk = False
    single = True

    async def execute(self, objects, db, user):
        for obj in objects:
            obj.is_active = False
        await db.commit()
        return {"summary": f"Disabled {len(objects)} tenant(s)", "affected": len(objects)}


class EnableTenantAction(AdminAction):
    name = "enable"
    label = "Enable tenant"
    danger = False
    confirm = True
    bulk = False
    single = True

    async def execute(self, objects, db, user):
        for obj in objects:
            obj.is_active = True
        await db.commit()
        return {"summary": f"Enabled {len(objects)} tenant(s)", "affected": len(objects)}


__all__ = [
    "BulkDeleteAction",
    "DeactivateUsersAction",
    "ActivateUsersAction",
    "DisableTenantAction",
    "EnableTenantAction",
]
