"""Default ModelAdmin registrations for the four framework models.

Registered by create_admin() only if the host app has not already registered
its own version.  Override any of these by registering a custom subclass
*before* calling create_admin():

    class MyUserAdmin(ModelAdmin):
        model = User
        list_display = ["email", "custom_field", ...]

    admin_site.register(MyUserAdmin())
    app = create_admin(config=...)
"""
from adminfoundry.actions import (
    ActivateUsersAction,
    BulkDeleteAction,
    DeactivateUsersAction,
    DisableTenantAction,
    EnableTenantAction,
)
from adminfoundry.admin.model_admin import ModelAdmin
from adminfoundry.admin.registry import admin_site
from adminfoundry.models.audit_log import AuditLog
from adminfoundry.models.role import Role
from adminfoundry.models.tenant import Tenant
from adminfoundry.models.user import User


class _DefaultUserAdmin(ModelAdmin):
    model = User
    label = "User"
    label_plural = "Users"
    description = "Registered application users"
    list_display = ["email", "full_name", "is_active", "is_superadmin"]
    search_fields = ["email", "full_name"]
    filter_fields = ["is_active", "is_superadmin"]
    ordering = ["email"]
    readonly_fields = ["id", "created_at", "updated_at"]
    protected_fields = ["tenant_id"]
    tenant_scoped = False
    extra_create_fields = {"set_password": str}
    actions = [DeactivateUsersAction(), ActivateUsersAction(), BulkDeleteAction()]

    @classmethod
    def before_create(cls, data: dict) -> dict:
        from adminfoundry.auth import hash_password
        plain = data.pop("set_password", None)
        if plain:
            data["hashed_password"] = hash_password(plain)
        return data


class _DefaultRoleAdmin(ModelAdmin):
    model = Role
    label = "Permission Group"
    label_plural = "Permissions"
    description = "Permission groups assignable to users — CRUD capabilities configured below"
    list_display = ["name", "description", "created_at"]
    search_fields = ["name"]
    ordering = ["name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    protected_fields = ["tenant_id"]
    tenant_scoped = True
    global_only_in_root_panel = True
    permission_matrix = True
    create_redirect = "detail"
    actions = [BulkDeleteAction()]


class _DefaultTenantAdmin(ModelAdmin):
    model = Tenant
    label = "Tenant"
    label_plural = "Tenants"
    description = "Tenant organisations"
    list_display = ["name", "slug", "is_active", "timezone", "language"]
    search_fields = ["name", "slug"]
    filter_fields = ["is_active"]
    ordering = ["slug"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = [DisableTenantAction(), EnableTenantAction()]


class _DefaultAuditLogAdmin(ModelAdmin):
    model = AuditLog
    label = "Audit Log"
    label_plural = "Audit Logs"
    description = "Immutable record of all admin actions"
    list_display = ["created_at", "actor", "action", "method", "path", "status_code", "object_id"]
    search_fields = ["actor", "path", "object_id", "action"]
    filter_fields = ["action", "method", "status_code"]
    range_filter_fields = ["created_at"]
    ordering = ["-created_at"]
    readonly_fields = [
        "id", "created_at", "updated_at", "method", "path", "status_code",
        "user_id", "tenant_id", "action", "object_id", "actor", "changes",
    ]
    tenant_scoped = False
    allow_delete = False
    actions = []


def register_framework_defaults(enable_multi_tenant: bool = False) -> None:
    """Register default admins for framework models not yet registered by the host app."""
    if not admin_site.get("users"):
        admin_site.register(_DefaultUserAdmin())
    if not admin_site.get("roles"):
        admin_site.register(_DefaultRoleAdmin())
    if enable_multi_tenant and not admin_site.get("tenants"):
        admin_site.register(_DefaultTenantAdmin())
    if not admin_site.get("audit_logs"):
        admin_site.register(_DefaultAuditLogAdmin())
