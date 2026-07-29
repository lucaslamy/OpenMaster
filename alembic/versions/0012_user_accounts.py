"""Add user accounts, revocable sessions, and project ownership."""

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create identities and make project ownership explicit."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="user", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.add_column("analysis_jobs", sa.Column("user_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_analysis_jobs_user_id_users",
        "analysis_jobs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_analysis_jobs_user_created", "analysis_jobs", ["user_id", "created_at"])


def downgrade() -> None:
    """Remove account ownership while retaining analysis jobs."""
    op.drop_index("ix_analysis_jobs_user_created", table_name="analysis_jobs")
    op.drop_constraint(
        "fk_analysis_jobs_user_id_users",
        "analysis_jobs",
        type_="foreignkey",
    )
    op.drop_column("analysis_jobs", "user_id")
    op.drop_table("user_sessions")
    op.drop_table("users")
