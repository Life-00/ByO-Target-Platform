"""
003_add_document_metadata_fields.py - Add PDF metadata fields to documents table.

This migration adds fields to track extracted PDF metadata:
- page_count: Number of pages in PDF
- keywords: Extracted keywords from PDF
- sections: Document sections/structure
- extracted_abstract: Abstract extracted from PDF
- relevance_score: LLM relevance score (0-1)
- source: Paper source (arxiv, pubmed)
- external_id: External paper ID (arxiv/pubmed)
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add metadata fields to documents table."""
    
    # Modify page_count to be nullable (was previously required)
    op.alter_column(
        "documents",
        "page_count",
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False,
    )
    
    # Add new metadata columns
    op.add_column("documents", sa.Column("keywords", sa.JSON(), nullable=True))
    op.add_column("documents", sa.Column("sections", sa.JSON(), nullable=True))
    op.add_column("documents", sa.Column("extracted_abstract", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("relevance_score", sa.Float(), nullable=True))
    op.add_column("documents", sa.Column("source", sa.String(length=50), nullable=True))
    op.add_column("documents", sa.Column("external_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove metadata fields from documents table."""
    
    op.drop_column("documents", "external_id")
    op.drop_column("documents", "source")
    op.drop_column("documents", "relevance_score")
    op.drop_column("documents", "extracted_abstract")
    op.drop_column("documents", "sections")
    op.drop_column("documents", "keywords")
    
    # Revert page_count to be required
    op.alter_column(
        "documents",
        "page_count",
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True,
    )
