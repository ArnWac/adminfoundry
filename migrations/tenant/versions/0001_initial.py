"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-06

Empty initial migration — tenant schemas are created dynamically via provisioning.
Tables specific to tenant schemas should be added here when introduced.
"""
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
