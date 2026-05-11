"""gdpr_and_2fa

Revision ID: 0008_gdpr_and_2fa
Revises: 0007_performance_indexes
Create Date: 2026-05-11

- audit_logs: add ip_address column
- users: add totp_secret, totp_enabled, totp_backup_codes columns
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_gdpr_and_2fa"
down_revision = "0007_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("ip_address", sa.String(45), nullable=True))
    op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("totp_backup_codes", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "totp_backup_codes")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
    op.drop_column("audit_logs", "ip_address")
