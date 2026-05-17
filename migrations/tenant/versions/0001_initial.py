"""Tenant schema initial tables: roles, role_permissions, membership_roles.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-17

Run against a specific tenant schema:

    alembic -c alembic_tenant.ini -x schema=tenant_acme upgrade head

The search_path is set to the target schema before these DDL statements run,
so all tables are created inside the tenant schema (not in public).

membership_roles.membership_id references public.tenant_memberships.id via a
cross-schema FK — valid in PostgreSQL; not applied on SQLite.
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_tenant_roles_name"),
    )
    op.create_index("ix_tenant_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_key", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission_key"),
    )

    op.create_table(
        "membership_roles",
        sa.Column("membership_id", sa.String(36), nullable=False),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("membership_id", "role_id"),
    )
    op.create_index("ix_membership_roles_membership_id", "membership_roles", ["membership_id"])

    # Cross-schema FK to public.tenant_memberships — PostgreSQL only
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_foreign_key(
            "fk_membership_roles_membership_id",
            "membership_roles",
            "tenant_memberships",
            ["membership_id"],
            ["id"],
            referent_schema="public",
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("fk_membership_roles_membership_id", "membership_roles", type_="foreignkey")
    op.drop_index("ix_membership_roles_membership_id", table_name="membership_roles")
    op.drop_table("membership_roles")
    op.drop_table("role_permissions")
    op.drop_index("ix_tenant_roles_name", table_name="roles")
    op.drop_table("roles")
