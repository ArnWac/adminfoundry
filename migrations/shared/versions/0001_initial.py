"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(63), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )
    op.create_index("ix_roles_name", "roles", ["name"])

    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            sa.String(36),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(50), nullable=True),
        sa.Column("object_id", sa.String(100), nullable=True),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("changes", sa.JSON(), nullable=True),
    )

    op.create_table(
        "impersonation_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superadmin_id", sa.String(36), nullable=False),
        sa.Column("target_user_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("jti", sa.String(100), nullable=False, unique=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_impersonation_logs_jti", "impersonation_logs", ["jti"])

    op.create_table(
        "change_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("object_id", sa.String(100), nullable=True),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("requester_id", sa.String(36), nullable=False),
        sa.Column("reviewer_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("proposed_data", sa.Text(), nullable=True),
        sa.Column("original_data", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("audit_log_id", sa.String(36), nullable=True),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("action_name", sa.String(100), nullable=True),
        sa.Column("initiator_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("audit_log_id", sa.String(36), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("failure_summary", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("input_data", sa.Text(), nullable=True),
        sa.Column("output_data", sa.Text(), nullable=True),
        sa.UniqueConstraint("idempotency_key", name="uq_jobs_idempotency_key"),
    )

    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(36), primary_key=True),
        sa.Column("exp", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "rate_limit_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("ts", sa.Float(), nullable=False),
    )
    op.create_index("ix_rate_limit_requests_key", "rate_limit_requests", ["key"])


def downgrade() -> None:
    op.drop_table("rate_limit_requests")
    op.drop_table("revoked_tokens")
    op.drop_table("jobs")
    op.drop_table("change_requests")
    op.drop_table("impersonation_logs")
    op.drop_table("audit_logs")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("tenants")
