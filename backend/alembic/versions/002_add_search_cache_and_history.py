"""
002_add_search_cache_and_history.py - Add search caching and history tables.

This migration creates tables for:
- search_cache: Caches search results with TTL
- search_history: Tracks user search history and statistics
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create search cache and history tables."""
    
    # Create search_cache table
    op.create_table(
        "search_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("papers_json", sa.Text(), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="604800"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accessed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "query_hash", "source", name="uq_search_cache_user_query_source"),
    )
    op.create_index("idx_search_cache_user_id", "search_cache", ["user_id"])
    op.create_index("idx_search_cache_query_hash", "search_cache", ["query_hash"])
    op.create_index("idx_search_cache_expires_at", "search_cache", ["expires_at"])
    
    # Create search_history table
    op.create_table(
        "search_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("query", sa.String(length=1000), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("papers_found", sa.Integer(), nullable=False),
        sa.Column("papers_downloaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("papers_filtered", sa.Integer(), nullable=False),
        sa.Column("min_relevance_score", sa.Float(), nullable=True),
        sa.Column("max_relevance_score", sa.Float(), nullable=True),
        sa.Column("avg_relevance_score", sa.Float(), nullable=True),
        sa.Column("search_time_seconds", sa.Float(), nullable=False),
        sa.Column("from_cache", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_search_history_user_id", "search_history", ["user_id"])
    op.create_index("idx_search_history_session_id", "search_history", ["session_id"])
    op.create_index("idx_search_history_created_at", "search_history", ["created_at"])


def downgrade() -> None:
    """Drop search cache and history tables."""
    
    # Drop search_history table
    op.drop_table("search_history")
    
    # Drop search_cache table
    op.drop_table("search_cache")
