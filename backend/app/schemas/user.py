"""
Pydantic schemas for user-related API requests and responses.

These schemas provide:
- Request validation for authentication endpoints
- Type-safe response models
- Automatic OpenAPI documentation
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.config.settings import settings


# ============================================================================
# Request Schemas (Input)
# ============================================================================


class UserRegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (3-50 characters)",
        pattern="^[a-zA-Z0-9_-]+$",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (8-128 characters)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "SecurePass123!",
            }
        }


class UserLoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
            }
        }


class TokenRefreshRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str = Field(..., description="Refresh token from login response")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }


class PasswordChangeRequest(BaseModel):
    """Request schema for password change."""

    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 characters)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewSecurePass456!",
            }
        }


# ============================================================================
# Response Schemas (Output)
# ============================================================================


class UserResponse(BaseModel):
    """User response schema (public info only)."""

    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "is_active": True,
                "created_at": "2026-01-17T10:30:00Z",
                "updated_at": "2026-01-17T10:30:00Z",
            }
        }


class TokenResponse(BaseModel):
    """Token response schema for authentication endpoints."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token (longer expiration)")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    user: UserResponse = Field(..., description="Authenticated user info")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "username": "johndoe",
                    "is_active": True,
                    "created_at": "2026-01-17T10:30:00Z",
                    "updated_at": "2026-01-17T10:30:00Z",
                },
            }
        }


class MessageResponse(BaseModel):
    """Generic message response schema."""

    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Whether operation succeeded")
    data: Optional[dict] = Field(None, description="Additional response data")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully",
                "success": True,
                "data": None,
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Detailed error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(settings.timezone), description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Email already registered",
                "status_code": 400,
                "timestamp": "2026-01-17T10:30:00+09:00",
            }
        }


# ============================================================================
# Utility Response Schemas
# ============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Health status")
    environment: str = Field(..., description="Environment name")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(settings.timezone), description="Timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "environment": "production",
                "version": "0.1.0",
                "timestamp": "2026-01-17T10:30:00+09:00",
            }
        }
