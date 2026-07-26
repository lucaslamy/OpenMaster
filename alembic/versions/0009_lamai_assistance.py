"""persist optional LamAI mastering assistance

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"


def upgrade() -> None:
    """Record whether a job requested LamAI advice."""
    op.add_column(
        "analysis_jobs",
        sa.Column("ai_assist_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Remove the optional LamAI assistance flag."""
    op.drop_column("analysis_jobs", "ai_assist_enabled")
