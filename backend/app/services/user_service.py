"""
User service for authentication and user management.

This service handles:
- User registration
- User login verification
- User retrieval
- Password management
- Database operations for users
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """Service for user-related database operations."""

    @staticmethod
    async def register_user(
        db: AsyncSession,
        email: str,
        username: str,
        password: str,
    ) -> Optional[User]:
        """Register a new user.
        
        Args:
            db: Async database session
            email: User email
            username: Username
            password: Plaintext password (will be hashed)
            
        Returns:
            Created User object if successful, None if email/username already exists
            
        Raises:
            sqlalchemy exceptions on database error
        """
        # Check if email already exists
        existing_email = await db.execute(
            select(User).where(User.email == email.lower())
        )
        if existing_email.scalars().first():
            logger.warning(f"Registration attempt with existing email: {email}")
            return None

        # Check if username already exists
        existing_username = await db.execute(
            select(User).where(User.username == username.lower())
        )
        if existing_username.scalars().first():
            logger.warning(f"Registration attempt with existing username: {username}")
            return None

        # Create new user
        hashed_password = hash_password(password)
        user = User(
            email=email.lower(),
            username=username.lower(),
            hashed_password=hashed_password,
            is_active=True,
        )

        db.add(user)
        await db.flush()  # Get user ID without committing
        await db.commit()

        logger.info(f"User registered successfully: {user.id} ({email})")
        return user

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address.
        
        Args:
            db: Async database session
            email: Email address to search for
            
        Returns:
            User object if found, None otherwise
        """
        result = await db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username.
        
        Args:
            db: Async database session
            username: Username to search for
            
        Returns:
            User object if found, None otherwise
        """
        result = await db.execute(
            select(User).where(User.username == username.lower())
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID.
        
        Args:
            db: Async database session
            user_id: User ID to search for
            
        Returns:
            User object if found, None otherwise
        """
        return await db.get(User, user_id)

    @staticmethod
    async def verify_user_password(
        user: User,
        password: str,
    ) -> bool:
        """Verify a user's password.
        
        Args:
            user: User object
            password: Plaintext password to verify
            
        Returns:
            True if password is correct, False otherwise
        """
        return verify_password(password, user.hashed_password)

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Optional[User]:
        """Authenticate a user by email and password.
        
        Args:
            db: Async database session
            email: User email
            password: Plaintext password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        user = await UserService.get_user_by_email(db, email)
        if not user:
            logger.warning(f"Login attempt with non-existent email: {email}")
            return None

        if not user.is_active:
            logger.warning(f"Login attempt with inactive user: {user.id}")
            return None

        if not await UserService.verify_user_password(user, password):
            logger.warning(f"Login attempt with wrong password: {email}")
            return None

        logger.info(f"User authenticated successfully: {user.id} ({email})")
        return user

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change user password.
        
        Args:
            db: Async database session
            user_id: User ID
            current_password: Current password for verification
            new_password: New password to set
            
        Returns:
            True if password changed successfully, False if current password is wrong
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return False

        # Verify current password
        if not await UserService.verify_user_password(user, current_password):
            logger.warning(f"Password change attempt with wrong current password: {user_id}")
            return False

        # Hash and update new password
        user.hashed_password = hash_password(new_password)
        db.add(user)
        await db.commit()

        logger.info(f"Password changed successfully: {user_id}")
        return True

    @staticmethod
    async def deactivate_user(db: AsyncSession, user_id: int) -> bool:
        """Deactivate a user account.
        
        Args:
            db: Async database session
            user_id: User ID to deactivate
            
        Returns:
            True if successful, False otherwise
        """
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return False

        user.is_active = False
        db.add(user)
        await db.commit()

        logger.info(f"User deactivated: {user_id}")
        return True
