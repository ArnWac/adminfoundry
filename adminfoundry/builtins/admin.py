from __future__ import annotations

from adminfoundry.models.tenant_rbac import (
    TenantMembershipRole,
    TenantRole,
    TenantRolePermission,
)
from adminfoundry.registry import ModelAdmin


class TenantRoleAdmin(ModelAdmin):
    model = TenantRole

    label = "Tenant Role"
    label_plural = "Tenant Roles"
    description = "Tenant-local roles used for permission assignment."

    list_display = ["name", "description", "is_system", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]
    readonly_fields = ["id", "created_at", "updated_at"]


class TenantRolePermissionAdmin(ModelAdmin):
    model = TenantRolePermission

    label = "Tenant Role Permission"
    label_plural = "Tenant Role Permissions"
    description = "Permission keys assigned to tenant-local roles."

    list_display = ["role_id", "permission_key", "created_at"]
    search_fields = ["permission_key"]
    ordering = ["permission_key"]
    readonly_fields = ["id", "created_at", "updated_at"]


class TenantMembershipRoleAdmin(ModelAdmin):
    model = TenantMembershipRole

    label = "Tenant Membership Role"
    label_plural = "Tenant Membership Roles"
    description = "Tenant-local mapping between a global TenantMembership and a tenant-local role."

    list_display = ["membership_id", "role_id", "created_at"]
    ordering = ["membership_id"]
    readonly_fields = ["id", "created_at", "updated_at"]


BUILTIN_TENANT_ADMINS = (
    TenantRoleAdmin,
    TenantRolePermissionAdmin,
    TenantMembershipRoleAdmin,
)


__all__ = [
    "BUILTIN_TENANT_ADMINS",
    "TenantMembershipRoleAdmin",
    "TenantRoleAdmin",
    "TenantRolePermissionAdmin",
]
