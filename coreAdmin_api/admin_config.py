"""
Admin registrations — import this module to activate them.

Note: admin CRUD for User is read/update only — use POST /api/v1/users to
create users (the admin create path lacks the password hashing step).
"""
from coreAdmin_api.admin import admin_site, ModelAdmin
from coreAdmin_api.models.role import Role
from coreAdmin_api.models.tenant import Tenant
from coreAdmin_api.models.user import User


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
    tenant_scoped = False
    actions = [
        {
            "name": "deactivate",
            "label": "Deactivate",
            "danger": True,
            "confirm": True,
            "bulk": True,
            "single": True,
        }
    ]


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
    actions = [
        {
            "name": "disable",
            "label": "Disable",
            "danger": True,
            "confirm": True,
            "bulk": False,
            "single": True,
        }
    ]


admin_site.register(UserAdmin())
admin_site.register(RoleAdmin())
admin_site.register(TenantAdmin())
