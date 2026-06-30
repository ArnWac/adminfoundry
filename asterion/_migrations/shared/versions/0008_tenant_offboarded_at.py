"""tenants.offboarded_at

Revision ID: 0008_tenant_offboarded_at
Revises: 0007_user_deactivated_at
Create Date: 2026-06-30

Adds ``tenants.offboarded_at`` (nullable, tz-aware) — when the tenant was
offboarded (roadmap G6). ``None`` means the tenant is live. In ``archive`` mode
the offboard flow keeps the row as a tombstone (``offboarded_at`` set +
``is_active=False``) so the slug stays reserved; ``drop`` mode deletes the row.
Nullable so existing rows remain valid.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Alembic identifiers
revision = "0008_tenant_offboarded_at"
down_revision = "0007_user_deactivated_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("offboarded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "offboarded_at")
