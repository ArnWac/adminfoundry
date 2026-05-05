"""
Admin registrations — import this module to activate them.

Note: admin CRUD for User is read/update only — use POST /api/v1/users to
create users (the admin create path lacks the password hashing step).
"""
from adminfoundry.admin import admin_site, ModelAdmin
from adminfoundry.admin.actions import AdminAction
from adminfoundry.auth import hash_password
from adminfoundry.models.role import Role
from adminfoundry.models.tenant import Tenant
from adminfoundry.models.user import User
from adminfoundry.settings import settings


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


class UserAdmin(ModelAdmin):
    model = User
    label = "User"
    label_plural = "Users"
    description = "Registered application users"
    list_display = ["email", "full_name", "is_active", "is_superadmin"]
    search_fields = ["email", "full_name"]
    filter_fields = ["is_active", "is_superadmin"]
    ordering = ["email"]
    readonly_fields = ["id", "created_at", "updated_at"]
    # hashed_password is globally protected — no need to list it here
    # tenant_id hidden when multi-tenant is disabled
    protected_fields = [] if settings.MULTI_TENANT else ["tenant_id"]
    tenant_scoped = False
    extra_create_fields = {"set_password": str}

    @classmethod
    def before_create(cls, data: dict) -> dict:
        plain = data.pop("set_password", None)
        if plain:
            data["hashed_password"] = hash_password(plain)
        return data
    actions = [DeactivateUsersAction()]


class RoleAdmin(ModelAdmin):
    model = Role
    label = "Role"
    label_plural = "Roles"
    description = "Permission roles assignable to users"
    list_display = ["name", "id"]
    search_fields = ["name"]
    ordering = ["name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = []


class TenantAdmin(ModelAdmin):
    model = Tenant
    label = "Tenant"
    label_plural = "Tenants"
    description = "Tenant organisations in multi-tenant mode"
    list_display = ["name", "slug", "is_active"]
    search_fields = ["name", "slug"]
    filter_fields = ["is_active"]
    ordering = ["slug"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = [DisableTenantAction()]


admin_site.register(UserAdmin())
admin_site.register(RoleAdmin())
if settings.MULTI_TENANT:
    admin_site.register(TenantAdmin())
