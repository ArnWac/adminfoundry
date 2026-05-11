"""token_version

Revision ID: 0009_token_version
Revises: 0008_gdpr_and_2fa
Create Date: 2026-05-11

- users: add token_version column for token invalidation on privilege change
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_token_version"
down_revision = "0008_gdpr_and_2fa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
