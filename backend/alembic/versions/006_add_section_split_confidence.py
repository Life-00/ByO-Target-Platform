"""Add section_split_confidence column to documents table

Revision ID: 006
Revises: 005
Create Date: 2026-01-19

Changes:
- Add section_split_confidence column to documents table to track whether section splitting used LLM or fallback
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add section_split_confidence column to documents table."""
    
    # Add section_split_confidence column with default value
    op.add_column(
        "documents",
        sa.Column("section_split_confidence", sa.String(50), nullable=False, server_default="unknown")
    )


def downgrade() -> None:
    """Remove section_split_confidence column from documents table."""
    
    op.drop_column("documents", "section_split_confidence")
