"""remove full_name column

Revision ID: 002_remove_full_name
Revises: 001_initial_schema
Create Date: 2026-01-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_remove_full_name'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove full_name column from users table."""
    op.drop_column('users', 'full_name')


def downgrade() -> None:
    """Add back full_name column to users table."""
    op.add_column('users', sa.Column('full_name', sa.String(length=255), nullable=True))
