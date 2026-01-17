"""
FastAPI dependency injection utilities.

Provides:
- get_current_user: Current authenticated user dependency
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.db.models import User
from app.utils.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """
    Dependency to get current authenticated user from JWT token.

    Extracts user_id, username, email from JWT token claims.
    Verifies user exists and is active.

    Args:
        token: JWT token from Authorization header (Bearer <token>)
        db: Database session for user lookup

    Returns:
        dict with user_id, username, email

    Raises:
        HTTPException 401: Invalid or expired token
        HTTPException 403: User account is deactivated

    Usage in route handlers:
        @router.get("/profile")
        async def get_profile(
            current_user: dict = Depends(get_current_user)
        ):
            user_id = current_user["user_id"]
            username = current_user["username"]
            email = current_user["email"]
            ...
    """
    # Decode JWT token
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Convert user_id to integer (JWT stores it as string)
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user exists and is active
    query = select(User).where(User.id == user_id_int)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    }
