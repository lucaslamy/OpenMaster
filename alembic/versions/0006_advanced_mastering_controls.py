"""persist advanced mastering controls

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade() -> None:
    """Add explicit EQ, clipper, and limiter settings."""
    columns = (
        ("eq_low_gain_db", "0.0"),
        ("eq_mid_gain_db", "0.0"),
        ("eq_high_gain_db", "0.0"),
        ("clipper_drive_db", "0.0"),
        ("limiter_lookahead_ms", "3.0"),
        ("limiter_release_ms", "80.0"),
    )
    for name, default in columns:
        op.add_column(
            "analysis_jobs",
            sa.Column(name, sa.Float(), nullable=False, server_default=default),
        )


def downgrade() -> None:
    """Remove advanced mastering controls in reverse dependency order."""
    for name in (
        "limiter_release_ms",
        "limiter_lookahead_ms",
        "clipper_drive_db",
        "eq_high_gain_db",
        "eq_mid_gain_db",
        "eq_low_gain_db",
    ):
        op.drop_column("analysis_jobs", name)
