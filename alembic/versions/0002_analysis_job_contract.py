"""persist complete analysis job contract

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    """Add durable upload, idempotency, result, and failure fields."""
    op.add_column("analysis_jobs", sa.Column("idempotency_key", sa.String(255)))
    op.add_column("analysis_jobs", sa.Column("object_name", sa.Text()))
    op.add_column("analysis_jobs", sa.Column("original_filename", sa.Text()))
    op.add_column(
        "analysis_jobs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("analysis_jobs", sa.Column("result", sa.JSON()))
    op.add_column("analysis_jobs", sa.Column("error_code", sa.String(64)))
    op.add_column("analysis_jobs", sa.Column("error_message", sa.Text()))
    op.add_column(
        "analysis_jobs",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_analysis_jobs_idempotency_key",
        "analysis_jobs",
        ["idempotency_key"],
    )
    op.alter_column("analysis_jobs", "updated_at", nullable=False)


def downgrade() -> None:
    """Restore the original minimal jobs table."""
    op.drop_constraint(
        "uq_analysis_jobs_idempotency_key",
        "analysis_jobs",
        type_="unique",
    )
    for name in (
        "updated_at",
        "error_message",
        "error_code",
        "result",
        "attempt_count",
        "original_filename",
        "object_name",
        "idempotency_key",
    ):
        op.drop_column("analysis_jobs", name)
