"""Admin registrations for the multi-tenant SaaS example.

Registers framework models (User, Role, Tenant, AuditLog) plus a tenant-scoped
domain model (Project). Tests rely on the exact shape of these registrations.
"""
from adminfoundry import (
    ModelAdmin, admin_site,
    BulkDeleteAction, DeactivateUsersAction, ActivateUsersAction,
    DisableTenantAction, EnableTenantAction,
)
from adminfoundry.auth import hash_password
from adminfoundry.models.audit_log import AuditLog
from adminfoundry.models.role import Role
from adminfoundry.models.role_permission import RolePermission  # noqa: F401 — register table
from adminfoundry.models.tenant import Tenant
from adminfoundry.models.user import User
from adminfoundry.settings import settings

from examples.basic_multi.models import Project


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
    # Users are global — tenant membership is handled via tenant-scoped roles
    protected_fields = ["tenant_id"]
    tenant_scoped = False
    extra_create_fields = {"set_password": str}

    @classmethod
    def before_create(cls, data: dict) -> dict:
        plain = data.pop("set_password", None)
        if plain:
            data["hashed_password"] = hash_password(plain)
        return data

    actions = [DeactivateUsersAction(), ActivateUsersAction(), BulkDeleteAction()]


class RoleAdmin(ModelAdmin):
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


class TenantAdmin(ModelAdmin):
    model = Tenant
    label = "Tenant"
    label_plural = "Tenants"
    description = "Tenant organisations in multi-tenant mode"
    list_display = ["name", "slug", "is_active", "timezone", "language"]
    search_fields = ["name", "slug"]
    filter_fields = ["is_active"]
    ordering = ["slug"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = [DisableTenantAction(), EnableTenantAction()]


class AuditLogAdmin(ModelAdmin):
    model = AuditLog
    label = "Audit Log"
    label_plural = "Audit Logs"
    description = "Immutable record of all admin actions"
    list_display = ["created_at", "actor", "action", "method", "path", "status_code", "object_id"]
    search_fields = ["actor", "path", "object_id", "action"]
    filter_fields = ["action", "method", "status_code"]
    range_filter_fields = ["created_at"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at", "method", "path", "status_code",
                       "user_id", "tenant_id", "action", "object_id", "actor", "changes"]
    tenant_scoped = False  # B2C: audit logs are superadmin-only, not visible to tenants
    allow_delete = False
    actions = []


class ProjectAdmin(ModelAdmin):
    model         = Project
    label         = "Project"
    label_plural  = "Projects"
    description   = "Projects of the active tenant"
    list_display  = ["name", "active", "created_at"]
    search_fields = ["name"]
    filter_fields = ["active"]
    ordering      = ["name"]
    readonly_fields = ["id", "created_at", "updated_at", "tenant_id"]
    tenant_scoped = True
    actions = [BulkDeleteAction()]


admin_site.register(UserAdmin())
admin_site.register(RoleAdmin())
admin_site.register(AuditLogAdmin())
admin_site.register(ProjectAdmin())
if settings.MULTI_TENANT:
    admin_site.register(TenantAdmin())
