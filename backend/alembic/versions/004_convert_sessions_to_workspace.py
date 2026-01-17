"""Convert sessions to workspace sessions

Revision ID: 004
Revises: 003
Create Date: 2026-01-17

Changes:
- Drop old login session columns (session_token, ip_address, user_agent, last_activity, expires_at)
- Add workspace session columns (title, description, updated_at)
- Convert sessions table from login tracking to workspace/chat sessions
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert sessions table to workspace sessions."""
    
    # Drop old indexes
    op.drop_index("idx_session_token", table_name="sessions")
    op.drop_index("idx_session_expires_at", table_name="sessions")
    
    # Drop old columns
    op.drop_column("sessions", "session_token")
    op.drop_column("sessions", "ip_address")
    op.drop_column("sessions", "user_agent")
    op.drop_column("sessions", "last_activity")
    op.drop_column("sessions", "expires_at")
    
    # Add new workspace columns
    op.add_column("sessions", sa.Column("title", sa.String(length=255), nullable=False, server_default="Untitled Session"))
    op.add_column("sessions", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("sessions", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    
    # Remove server_default after adding column
    op.alter_column("sessions", "title", server_default=None)
    
    # Add new index
    op.create_index("idx_session_created_at", "sessions", ["created_at"])


def downgrade() -> None:
    """Revert workspace sessions back to login sessions."""
    
    # Drop workspace columns and indexes
    op.drop_index("idx_session_created_at", table_name="sessions")
    op.drop_column("sessions", "updated_at")
    op.drop_column("sessions", "description")
    op.drop_column("sessions", "title")
    
    # Restore old login session columns
    op.add_column("sessions", sa.Column("session_token", sa.String(length=255), nullable=False))
    op.add_column("sessions", sa.Column("ip_address", sa.String(length=45), nullable=True))
    op.add_column("sessions", sa.Column("user_agent", sa.String(length=500), nullable=True))
    op.add_column("sessions", sa.Column("last_activity", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column("sessions", sa.Column("expires_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    
    # Restore old indexes
    op.create_index("idx_session_token", "sessions", ["session_token"])
    op.create_index("idx_session_expires_at", "sessions", ["expires_at"])
    op.create_unique_constraint("sessions_session_token_key", "sessions", ["session_token"])
