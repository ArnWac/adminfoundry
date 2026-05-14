"""Admin registrations for the multi-tenant SaaS example.

Framework models (User, Role, Tenant, AuditLog) are registered automatically
by create_admin() with sensible defaults.  Only the app-specific Project model
needs an explicit registration here.
"""
from adminfoundry import ModelAdmin, admin_site, BulkDeleteAction

from examples.basic_multi.models import Project


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


admin_site.register(ProjectAdmin())
