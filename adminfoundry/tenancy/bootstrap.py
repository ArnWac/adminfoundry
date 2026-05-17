"""Tenant bootstrap service.

Called when a new tenant is provisioned. Idempotent: safe to run multiple times.

Steps:
1. Create PostgreSQL schema.
2. Run tenant Alembic migrations.
3. Seed default roles (owner, admin, viewer).
4. Seed role_permissions from public.permission_catalog.
5. Assign owner role to initial membership (if provided).
6. Write audit log entry.
"""
from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.tenancy.schema_strategy import _validate_schema_name, get_tenant_session
from adminfoundry.tenancy.tenant_models import TenantMembershipRole, TenantRole, TenantRolePermission

# Roles created in every new tenant schema.
_DEFAULT_ROLES: list[dict] = [
    {"name": "owner", "description": "Full tenant access", "is_system": True},
    {"name": "admin", "description": "Administrative access", "is_system": True},
    {"name": "viewer", "description": "Read-only access", "is_system": True},
]

# Default permission keys granted to owner and admin roles.
# Seeded from public.permission_catalog after catalog rows exist.
_OWNER_PERMISSIONS: set[str] = set()   # filled from catalog — owner gets all keys
_ADMIN_PERMISSIONS_DENY: set[str] = {  # keys explicitly withheld from admin
    "admin.audit.delete",
    "admin.users.delete",
}
_VIEWER_KEYS: list[str] = []   # viewer gets no write keys (list only, set per model)


async def bootstrap_tenant(
    slug: str,
    public_db: AsyncSession,
    owner_membership_id: uuid.UUID | None = None,
) -> None:
    """Provision a tenant schema and seed it with default roles and permissions.

    Schema-per-tenant requires PostgreSQL. On other databases this is a no-op
    so that unit tests running on SQLite are not affected.

    Args:
        slug: Tenant slug (used to derive schema name).
        public_db: Open session on the public/shared schema.
        owner_membership_id: If provided, assigns the owner role to this membership.
    """
    from adminfoundry.settings import settings

    if "postgresql" not in settings.DATABASE_URL:
        return

    schema_name = f"tenant_{slug}"
    _validate_schema_name(schema_name)

    # 1. Create schema (idempotent)
    await _create_schema(schema_name, public_db)

    # 2. Run tenant Alembic migrations
    _run_tenant_migrations(schema_name)

    # 3-5. Seed RBAC inside the tenant schema
    async for tenant_db in get_tenant_session(schema_name):
        await _seed_roles(tenant_db, public_db, owner_membership_id)

    # 6. Audit log
    await _write_audit(schema_name, public_db)


async def _create_schema(schema_name: str, db: AsyncSession) -> None:
    """CREATE SCHEMA IF NOT EXISTS."""
    await db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    await db.commit()


def _run_tenant_migrations(schema_name: str) -> None:
    """Run alembic tenant migrations for the given schema name."""
    # Locate alembic_tenant.ini relative to the package root.
    ini_path = Path(__file__).parent.parent.parent / "alembic_tenant.ini"
    if not ini_path.exists():
        raise FileNotFoundError(f"alembic_tenant.ini not found at {ini_path}")

    result = subprocess.run(
        [
            sys.executable, "-m", "alembic",
            "-c", str(ini_path),
            "-x", f"schema={schema_name}",
            "upgrade", "head",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Tenant migration failed for schema {schema_name!r}:\n"
            f"{result.stderr}"
        )


async def _seed_roles(
    tenant_db: AsyncSession,
    public_db: AsyncSession,
    owner_membership_id: uuid.UUID | None,
) -> None:
    """Seed default roles, their permissions, and optionally assign owner role."""
    from adminfoundry.models.permission_catalog import PermissionCatalog

    # Load all permission keys from catalog
    catalog_rows = (
        await public_db.execute(select(PermissionCatalog.key))
    ).scalars().all()
    all_keys = set(catalog_rows)

    role_map: dict[str, TenantRole] = {}
    for role_def in _DEFAULT_ROLES:
        existing = (
            await tenant_db.execute(
                select(TenantRole).where(TenantRole.name == role_def["name"])
            )
        ).scalar_one_or_none()
        if existing is None:
            role = TenantRole(**role_def)
            tenant_db.add(role)
            await tenant_db.flush()
        else:
            role = existing
        role_map[role_def["name"]] = role

    # Grant permissions: owner → all keys; admin → all minus deny-list; viewer → list keys only
    await _grant_permissions(tenant_db, role_map["owner"], all_keys)
    await _grant_permissions(
        tenant_db, role_map["admin"],
        {k for k in all_keys if k not in _ADMIN_PERMISSIONS_DENY},
    )
    viewer_keys = {k for k in all_keys if k.endswith(".list")}
    await _grant_permissions(tenant_db, role_map["viewer"], viewer_keys)

    if owner_membership_id is not None:
        owner_role = role_map["owner"]
        existing_mr = (
            await tenant_db.execute(
                select(TenantMembershipRole).where(
                    TenantMembershipRole.membership_id == owner_membership_id,
                    TenantMembershipRole.role_id == owner_role.id,
                )
            )
        ).scalar_one_or_none()
        if existing_mr is None:
            tenant_db.add(
                TenantMembershipRole(
                    membership_id=owner_membership_id,
                    role_id=owner_role.id,
                )
            )

    await tenant_db.commit()


async def _grant_permissions(
    db: AsyncSession, role: TenantRole, keys: set[str]
) -> None:
    """Insert missing role_permission rows for the given key set (idempotent)."""
    existing_keys = set(
        (
            await db.execute(
                select(TenantRolePermission.permission_key).where(
                    TenantRolePermission.role_id == role.id
                )
            )
        ).scalars().all()
    )
    for key in keys - existing_keys:
        db.add(TenantRolePermission(role_id=role.id, permission_key=key))


async def _write_audit(schema_name: str, db: AsyncSession) -> None:
    """Write a tenant.created audit log entry into public.audit_logs."""
    from adminfoundry.models.audit_log import AuditLog

    db.add(
        AuditLog(
            method="INTERNAL",
            path="/tenancy/bootstrap",
            status_code=0,
            action="tenant.created",
            changes={"schema_name": schema_name},
        )
    )
    await db.commit()
