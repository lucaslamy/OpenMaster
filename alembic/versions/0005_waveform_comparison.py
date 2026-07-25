"""persist waveform comparison envelopes

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    """Add compact source and master waveform envelopes."""
    op.add_column("analysis_jobs", sa.Column("source_waveform", sa.JSON()))
    op.add_column("analysis_jobs", sa.Column("master_waveform", sa.JSON()))


def downgrade() -> None:
    """Remove waveform comparison envelopes."""
    op.drop_column("analysis_jobs", "master_waveform")
    op.drop_column("analysis_jobs", "source_waveform")
