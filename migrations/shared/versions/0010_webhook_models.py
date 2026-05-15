"""webhook_models

Revision ID: 0010_webhook_models
Revises: 0009_token_version
Create Date: 2026-05-16

- Create webhook_subscriptions table
- Create webhook_deliveries table
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_webhook_models"
down_revision = "0009_token_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("events", sa.Text(), nullable=False),
        sa.Column("secret", sa.String(512), nullable=True),
        sa.Column("model_filter", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.String(36), nullable=True, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subscription_id", sa.String(36), nullable=False, index=True),
        sa.Column("event", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_subscriptions")
