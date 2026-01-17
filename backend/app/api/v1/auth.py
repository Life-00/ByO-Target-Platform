"""
Authentication API routes.

Endpoints:
- POST /auth/register - User registration (create account)
- POST /auth/login - User login (get tokens)
- POST /auth/refresh - Refresh access token
"""

import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.database import get_db_session
from app.schemas.user import (
    MessageResponse,
    PasswordChangeRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.user_service import UserService
from app.utils.security import create_access_token, create_refresh_token, verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================================================
# Registration Endpoint
# ============================================================================


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
async def register(
    request: UserRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    """Register a new user account.
    
    Creates a new user with email, username, and password.
    Returns access and refresh tokens if successful.
    
    Args:
        request: Registration request data
        db: Database session (injected)
        
    Returns:
        TokenResponse with access token, refresh token, and user info
        
    Raises:
        HTTPException 400: Email or username already registered
        HTTPException 500: Database error
        
    Example:
        ```json
        POST /api/v1/auth/register
        {
            "email": "user@example.com",
            "username": "johndoe",
            "password": "SecurePass123!"
        }
        ```
    """
    try:
        # Attempt to register user
        user = await UserService.register_user(
            db=db,
            email=request.email,
            username=request.username,
            password=request.password,
        )

        if not user:
            # Email or username already exists
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or username already registered",
            )

        # Generate tokens
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires,
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=UserResponse.model_validate(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration",
        )


# ============================================================================
# Login Endpoint
# ============================================================================


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
)
async def login(
    request: UserLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    """Authenticate user and return tokens.
    
    Verifies email and password, returns access and refresh tokens if valid.
    
    Args:
        request: Login request data (email, password)
        db: Database session (injected)
        
    Returns:
        TokenResponse with access token, refresh token, and user info
        
    Raises:
        HTTPException 401: Invalid email or password
        HTTPException 500: Database error
        
    Example:
        ```json
        POST /api/v1/auth/login
        {
            "email": "user@example.com",
            "password": "SecurePass123!"
        }
        ```
    """
    try:
        # Authenticate user
        user = await UserService.authenticate_user(
            db=db,
            email=request.email,
            password=request.password,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate tokens
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires,
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=UserResponse.model_validate(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login",
        )


# ============================================================================
# Token Refresh Endpoint
# ============================================================================


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    request: TokenRefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    """Refresh access token using refresh token.
    
    Validates refresh token and issues new access token.
    
    Args:
        request: Refresh token request
        db: Database session (injected)
        
    Returns:
        TokenResponse with new access token
        
    Raises:
        HTTPException 401: Invalid or expired refresh token
        HTTPException 404: User not found
        
    Example:
        ```json
        POST /api/v1/auth/refresh
        {
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
        ```
    """
    # Verify refresh token
    user_id = verify_token(request.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    user = await UserService.get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate new access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        user=UserResponse.model_validate(user),
    )


# ============================================================================
# Password Management Endpoints
# ============================================================================

# TODO: Uncomment after fixing circular dependency with get_current_user
# @router.post("/change-password", response_model=MessageResponse)
# async def change_password(
#     request: PasswordChangeRequest,
#     current_user: int = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db_session),
# ):
#     """Change user password.
#     
#     Requires current password for verification.
#     Only accessible to authenticated users.
#     
#     Args:
#         request: Password change request (current and new password)
#         current_user: Current user ID (injected from token)
#         db: Database session (injected)
#         
#     Returns:
#         MessageResponse confirming password change
#         
#     Raises:
#         HTTPException 401: Invalid current password
#         HTTPException 404: User not found
#         HTTPException 500: Database error
#         
#     Example:
#         ```json
#         POST /api/v1/auth/change-password
#         Authorization: Bearer <access_token>
#         {
#             "current_password": "OldPassword123!",
#             "new_password": "NewSecurePass456!"
#         }
#         ```
#     """
#     try:
#         success = await UserService.change_password(
#             db=db,
#             user_id=current_user,
#             current_password=request.current_password,
#             new_password=request.new_password,
#         )
#
#         if not success:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Current password is incorrect",
#             )
#
#         return MessageResponse(
#             message="Password changed successfully",
#             success=True,
#         )
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Password change error: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error during password change",
#         )


# ============================================================================
# Helper Functions
# ============================================================================
async def get_current_user(
    authorization: str = None,
    db: AsyncSession = Depends(get_db_session),
) -> int:
    """Extract and validate current user from authorization header.
    
    This is a dependency function for protecting endpoints.
    
    Args:
        authorization: Authorization header value
        db: Database session
        
    Returns:
        User ID if token is valid
        
    Raises:
        HTTPException 401: Missing or invalid token
        
    Usage:
        ```python
        @router.get("/protected")
        async def protected_endpoint(
            current_user: int = Depends(get_current_user)
        ):
            return {"user_id": current_user}
        ```
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Verify token
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    user = await UserService.get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return int(user_id)
