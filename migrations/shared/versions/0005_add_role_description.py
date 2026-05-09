"""add role description field

Revision ID: 0005_add_role_description
Revises: 0004_add_tenant_locale
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0005_add_role_description"
down_revision = "0004_add_tenant_locale"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("roles", sa.Column("description", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("roles", "description")
