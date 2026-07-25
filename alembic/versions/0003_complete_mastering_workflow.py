"""persist complete mastering workflow

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    """Add recommendation, mastering, output, and requested-setting fields."""
    op.add_column("analysis_jobs", sa.Column("recommendation", sa.JSON()))
    op.add_column("analysis_jobs", sa.Column("mastering_result", sa.JSON()))
    op.add_column("analysis_jobs", sa.Column("output_object_name", sa.Text()))
    op.add_column(
        "analysis_jobs",
        sa.Column("target_lufs", sa.Float(), nullable=False, server_default="-14.0"),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("bit_depth", sa.Integer(), nullable=False, server_default="24"),
    )


def downgrade() -> None:
    """Remove complete-workflow fields."""
    for name in (
        "bit_depth",
        "target_lufs",
        "output_object_name",
        "mastering_result",
        "recommendation",
    ):
        op.drop_column("analysis_jobs", name)
