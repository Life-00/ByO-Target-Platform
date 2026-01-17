"""Generic single-database configuration."""

from __future__ import annotations

from alembic import command
from alembic.config import Config


# Alembic initialization configuration
# This file is used by alembic for database versioning


def get_alembic_config() -> Config:
    """Get Alembic configuration object.
    
    Returns:
        Config: Alembic configuration
    """
    config = Config("alembic.ini")
    return config


async def upgrade_database():
    """Apply all pending database migrations.
    
    Usage:
        await upgrade_database()
    """
    config = get_alembic_config()
    command.upgrade(config, "head")


async def downgrade_database(revision: str = "-1"):
    """Revert database migrations.
    
    Args:
        revision: Revision to downgrade to (default: "-1" for last migration)
    
    Usage:
        await downgrade_database()  # Revert last
        await downgrade_database("base")  # Revert all
    """
    config = get_alembic_config()
    command.downgrade(config, revision)


async def create_migration(message: str, autogenerate: bool = True):
    """Create a new database migration.
    
    Args:
        message: Migration description
        autogenerate: Auto-detect model changes
    
    Usage:
        await create_migration("Add user table")
    """
    config = get_alembic_config()
    if autogenerate:
        command.revision(config, message=message, autogenerate=True)
    else:
        command.revision(config, message=message)
