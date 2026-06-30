"""users.deactivated_at

Revision ID: 0007_user_deactivated_at
Revises: 0006_impersonation_reason
Create Date: 2026-06-30

Adds ``users.deactivated_at`` (nullable, tz-aware) — when the account was
deactivated. Starts the G2 retention clock: ``privacy retention-run``
auto-anonymises accounts whose ``deactivated_at`` is older than
``user_anonymize_after_days``. Nullable so existing rows (and active accounts)
remain valid; ``None`` means "active / never deactivated".
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Alembic identifiers
revision = "0007_user_deactivated_at"
down_revision = "0006_impersonation_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "deactivated_at")
