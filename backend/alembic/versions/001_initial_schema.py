"""
001_initial_schema.py - Initial database schema migration.

This migration creates all base tables for the ScholarLens application:
- users: User accounts and authentication
- sessions: User session tracking
- documents: PDF documents
- document_chunks: Text chunks for vector search
- chat_messages: Chat history
- analysis_reports: Generated reports
- document_annotations: User annotations
- agent_logs: Agent execution logs
- api_usage: API usage tracking
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("idx_user_email", "users", ["email"])
    op.create_index("idx_user_username", "users", ["username"])

    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_activity", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token"),
    )
    op.create_index("idx_session_token", "sessions", ["session_token"])
    op.create_index("idx_session_user_id", "sessions", ["user_id"])
    op.create_index("idx_session_expires_at", "sessions", ["expires_at"])

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=50), nullable=False, server_default="application/pdf"),
        sa.Column("is_indexed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_document_user_id", "documents", ["user_id"])
    op.create_index("idx_document_indexed", "documents", ["is_indexed"])

    # Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("chroma_id", sa.String(length=36), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chroma_id"),
    )
    op.create_index("idx_chunk_document_id", "document_chunks", ["document_id"])
    op.create_index("idx_chunk_chroma_id", "document_chunks", ["chroma_id"])
    op.create_index("idx_chunk_page_number", "document_chunks", ["page_number"])

    # Create chat_messages table
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_message_user_id", "chat_messages", ["user_id"])
    op.create_index("idx_message_document_id", "chat_messages", ["document_id"])
    op.create_index("idx_message_created_at", "chat_messages", ["created_at"])

    # Create analysis_reports table
    op.create_table(
        "analysis_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("agent_type", sa.String(length=50), nullable=False),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_report_document_id", "analysis_reports", ["document_id"])
    op.create_index("idx_report_agent_type", "analysis_reports", ["agent_type"])

    # Create document_annotations table
    op.create_table(
        "document_annotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("highlight_text", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("annotation_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_annotation_document_id", "document_annotations", ["document_id"])
    op.create_index("idx_annotation_user_id", "document_annotations", ["user_id"])

    # Create agent_logs table
    op.create_table(
        "agent_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=True),
        sa.Column("output_data", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_agent_log_agent_name", "agent_logs", ["agent_name"])
    op.create_index("idx_agent_log_document_id", "agent_logs", ["document_id"])
    op.create_index("idx_agent_log_status", "agent_logs", ["status"])
    op.create_index("idx_agent_log_created_at", "agent_logs", ["created_at"])

    # Create api_usage table
    op.create_table(
        "api_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("request_size_bytes", sa.Integer(), nullable=True),
        sa.Column("response_size_bytes", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_usage_user_id", "api_usage", ["user_id"])
    op.create_index("idx_usage_endpoint", "api_usage", ["endpoint"])
    op.create_index("idx_usage_created_at", "api_usage", ["created_at"])


def downgrade() -> None:
    """Drop all tables (rollback initial schema)."""
    op.drop_index("idx_usage_created_at", table_name="api_usage")
    op.drop_index("idx_usage_endpoint", table_name="api_usage")
    op.drop_index("idx_usage_user_id", table_name="api_usage")
    op.drop_table("api_usage")

    op.drop_index("idx_agent_log_created_at", table_name="agent_logs")
    op.drop_index("idx_agent_log_status", table_name="agent_logs")
    op.drop_index("idx_agent_log_document_id", table_name="agent_logs")
    op.drop_index("idx_agent_log_agent_name", table_name="agent_logs")
    op.drop_table("agent_logs")

    op.drop_index("idx_annotation_user_id", table_name="document_annotations")
    op.drop_index("idx_annotation_document_id", table_name="document_annotations")
    op.drop_table("document_annotations")

    op.drop_index("idx_report_agent_type", table_name="analysis_reports")
    op.drop_index("idx_report_document_id", table_name="analysis_reports")
    op.drop_table("analysis_reports")

    op.drop_index("idx_message_created_at", table_name="chat_messages")
    op.drop_index("idx_message_document_id", table_name="chat_messages")
    op.drop_index("idx_message_user_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("idx_chunk_page_number", table_name="document_chunks")
    op.drop_index("idx_chunk_chroma_id", table_name="document_chunks")
    op.drop_index("idx_chunk_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("idx_document_indexed", table_name="documents")
    op.drop_index("idx_document_user_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("idx_session_expires_at", table_name="sessions")
    op.drop_index("idx_session_user_id", table_name="sessions")
    op.drop_index("idx_session_token", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("idx_user_username", table_name="users")
    op.drop_index("idx_user_email", table_name="users")
    op.drop_table("users")
