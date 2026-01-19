"""Add analysis_goal column to sessions table

Revision ID: 005
Revises: 004
Create Date: 2026-01-18

Changes:
- Add analysis_goal column to sessions table to store user's analysis target/goal per workspace
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add analysis_goal column to sessions table."""
    
    # Add analysis_goal column (nullable for existing sessions)
    op.add_column(
        "sessions",
        sa.Column("analysis_goal", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Remove analysis_goal column from sessions table."""
    
    op.drop_column("sessions", "analysis_goal")
