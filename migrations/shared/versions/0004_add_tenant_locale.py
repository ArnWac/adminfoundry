"""add tenant locale fields

Revision ID: 0004_add_tenant_locale
Revises: 0003_add_role_permissions
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0004_add_tenant_locale"
down_revision = "0003_add_role_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("timezone", sa.String(64), nullable=True))
    op.add_column("tenants", sa.Column("language", sa.String(16), nullable=True))
    op.add_column("tenants", sa.Column("date_format", sa.String(16), nullable=True))
    op.add_column("tenants", sa.Column("date_pattern", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "date_pattern")
    op.drop_column("tenants", "date_format")
    op.drop_column("tenants", "language")
    op.drop_column("tenants", "timezone")
