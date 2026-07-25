"""persist mastering policy controls

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    """Add explicit peak ceiling and maximum gain controls."""
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "maximum_gain_adjustment_db",
            sa.Float(),
            nullable=False,
            server_default="12.0",
        ),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("ceiling_dbfs", sa.Float(), nullable=False, server_default="-1.0"),
    )


def downgrade() -> None:
    """Remove explicit mastering policy controls."""
    op.drop_column("analysis_jobs", "ceiling_dbfs")
    op.drop_column("analysis_jobs", "maximum_gain_adjustment_db")
