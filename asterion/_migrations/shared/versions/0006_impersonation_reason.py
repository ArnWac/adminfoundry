"""impersonation_logs.reason

Revision ID: 0006_impersonation_reason
Revises: 0005_user_is_service_account
Create Date: 2026-06-29

Adds ``impersonation_logs.reason`` (nullable text, max 500) — the documented
purpose of a support impersonation (G9). Nullable so existing rows and
deployments running with ``impersonation_require_reason=False`` remain valid;
the route enforces presence when the config flag is on.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Alembic identifiers
revision = "0006_impersonation_reason"
down_revision = "0005_user_is_service_account"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "impersonation_logs",
        sa.Column("reason", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("impersonation_logs", "reason")
