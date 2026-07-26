"""Persist interactive settings and final-render lineage."""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_jobs", sa.Column("initial_output_object_name", sa.Text()))
    op.add_column("analysis_jobs", sa.Column("parent_job_id", sa.String(36)))
    op.add_column("analysis_jobs", sa.Column("interactive_settings", sa.JSON()))
    op.create_index("ix_analysis_jobs_parent_job_id", "analysis_jobs", ["parent_job_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_parent_job_id", table_name="analysis_jobs")
    op.drop_column("analysis_jobs", "interactive_settings")
    op.drop_column("analysis_jobs", "parent_job_id")
    op.drop_column("analysis_jobs", "initial_output_object_name")
