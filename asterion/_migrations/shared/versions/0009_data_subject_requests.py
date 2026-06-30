"""data_subject_requests

Revision ID: 0009_data_subject_requests
Revises: 0008_tenant_offboarded_at
Create Date: 2026-06-30

Adds the ``data_subject_requests`` DSAR log table (roadmap G8): a register of
GDPR data-subject requests (access / export / rectification / erasure /
restriction) — who/what/when/result — backing Art. 15/16/17/18/20
accountability. Public/global table; data-subject rights are about a ``users``
row, which lives in the public schema.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from asterion.models.base import GUID

# Alembic identifiers
revision = "0009_data_subject_requests"
down_revision = "0008_tenant_offboarded_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_subject_requests",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("subject_user_id", GUID(), nullable=False),
        sa.Column("request_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("handled_by_user_id", GUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_subject_requests_subject_user_id",
        "data_subject_requests",
        ["subject_user_id"],
    )
    op.create_index(
        "ix_dsar_subject_created",
        "data_subject_requests",
        ["subject_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_dsar_subject_created", table_name="data_subject_requests")
    op.drop_index(
        "ix_data_subject_requests_subject_user_id", table_name="data_subject_requests"
    )
    op.drop_table("data_subject_requests")
