"""Add an editable display name to retained projects."""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store a user-facing name independently from the immutable source filename."""
    op.add_column("analysis_jobs", sa.Column("project_name", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove editable project names."""
    op.drop_column("analysis_jobs", "project_name")
