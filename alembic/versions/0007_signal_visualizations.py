"""persist compact signal visualizations

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade() -> None:
    """Add source/master spectral and temporal level summaries."""
    for name in (
        "source_spectrum",
        "master_spectrum",
        "source_level_timeline",
        "master_level_timeline",
    ):
        op.add_column("analysis_jobs", sa.Column(name, sa.JSON()))


def downgrade() -> None:
    """Remove compact signal visualizations."""
    for name in (
        "master_level_timeline",
        "source_level_timeline",
        "master_spectrum",
        "source_spectrum",
    ):
        op.drop_column("analysis_jobs", name)
