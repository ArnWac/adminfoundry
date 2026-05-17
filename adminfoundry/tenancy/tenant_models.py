"""Tenant-local RBAC models — live in the active tenant schema, not in public.

These models inherit TenantBase so their metadata is separate from the global
Base.metadata. They have no tenant_id column: the PostgreSQL schema itself
provides the tenant boundary.

TenantMembershipRole.membership_id is a cross-schema FK to
public.tenant_memberships.id. This is a PostgreSQL-only constraint; SQLite
tests do not create these tables.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, PrimaryKeyConstraint, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adminfoundry.models.base import GUID, TenantBase, TenantTimestampedBase


class TenantRole(TenantTimestampedBase):
    __tablename__ = "roles"
    __table_args__ = (Index("ix_tenant_roles_name", "name", unique=True),)

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions: Mapped[list[TenantRolePermission]] = relationship(
        "TenantRolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    membership_roles: Mapped[list[TenantMembershipRole]] = relationship(
        "TenantMembershipRole", back_populates="role", cascade="all, delete-orphan"
    )


class TenantRolePermission(TenantBase):
    """Maps a tenant-local role to a permission key from public.permission_catalog."""

    __tablename__ = "role_permissions"
    __table_args__ = (PrimaryKeyConstraint("role_id", "permission_key"),)

    role_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_key: Mapped[str] = mapped_column(String(200), nullable=False)

    role: Mapped[TenantRole] = relationship("TenantRole", back_populates="permissions")


class TenantMembershipRole(TenantBase):
    """Assigns a tenant-local role to a global TenantMembership.

    membership_id references public.tenant_memberships.id (cross-schema FK,
    PostgreSQL only). role_id references roles.id in the active tenant schema.
    """

    __tablename__ = "membership_roles"
    __table_args__ = (PrimaryKeyConstraint("membership_id", "role_id"),)

    membership_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("public.tenant_memberships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )

    role: Mapped[TenantRole] = relationship("TenantRole", back_populates="membership_roles")
