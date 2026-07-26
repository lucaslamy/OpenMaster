"""persist complete mastering-chain controls

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"


def upgrade() -> None:
    """Add subsonic, selective-dynamics, and saturation settings."""
    op.add_column(
        "analysis_jobs",
        sa.Column("high_pass_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    for name, default in (
        ("high_pass_cutoff_hz", "25.0"),
        ("dynamic_eq_reduction_db", "0.0"),
        ("bass_control_reduction_db", "0.0"),
        ("de_esser_reduction_db", "0.0"),
        ("saturation_amount", "0.0"),
    ):
        op.add_column(
            "analysis_jobs",
            sa.Column(name, sa.Float(), nullable=False, server_default=default),
        )


def downgrade() -> None:
    """Remove complete-chain settings in reverse order."""
    for name in (
        "saturation_amount",
        "de_esser_reduction_db",
        "bass_control_reduction_db",
        "dynamic_eq_reduction_db",
        "high_pass_cutoff_hz",
        "high_pass_enabled",
    ):
        op.drop_column("analysis_jobs", name)
