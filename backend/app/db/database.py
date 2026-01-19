"""
Database connection and session management.

This module provides:
- SQLAlchemy engine and session factory
- Database initialization
- Async session management with context managers
- Connection pooling configuration
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.db.models import Base


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_size=20,  # Maximum number of persistent connections
    max_overflow=10,  # Maximum overflow connections
    pool_pre_ping=True,  # Test connection before using
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database tables if they don't exist.
    
    This is called on application startup to ensure all tables are created.
    If using Alembic migrations in production, this can be skipped.
    """
    async with engine.begin() as conn:
        # Create all tables defined in models
        # In production with Alembic, use: alembic upgrade head
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close all database connections.
    
    This is called on application shutdown to properly close the connection pool.
    """
    await engine.dispose()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for dependency injection.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            items = await db.execute(select(Item))
            return items.scalars().all()
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class DatabaseManager:
    """Manager class for database operations."""

    @staticmethod
    async def init() -> None:
        """Initialize database on startup."""
        await init_db()

    @staticmethod
    async def close() -> None:
        """Close database on shutdown."""
        await close_db()

    @staticmethod
    async def health_check() -> bool:
        """Check database connection health.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
