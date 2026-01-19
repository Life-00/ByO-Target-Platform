"""
Pydantic schemas for session-related API requests and responses.

These schemas provide:
- Session creation and management request/response models
- Type-safe session data validation
- Automatic OpenAPI documentation
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas (Input)
# ============================================================================


class SessionCreateRequest(BaseModel):
    """Request schema for creating a new session."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Session title (1-255 characters)",
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional session description (up to 1000 characters)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Drug Target Analysis - January 2026",
                "description": "Session for analyzing potential drug targets in cancer research",
            }
        }


class SessionUpdateRequest(BaseModel):
    """Request schema for updating session metadata."""

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="New session title",
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="New session description",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Session Title",
                "description": "Updated description",
            }
        }


# ============================================================================
# Response Schemas (Output)
# ============================================================================


class SessionUpdate(BaseModel):
    """Schema for updating a session."""

    analysis_goal: Optional[str] = Field(None, description="Analysis goal/target for this session")

    class Config:
        json_schema_extra = {
            "example": {
                "analysis_goal": "Focus on kinase inhibitor targets in cancer research"
            }
        }


class SessionResponse(BaseModel):
    """Response schema for a single session."""

    id: int = Field(..., description="Unique session ID")
    user_id: int = Field(..., description="User ID who owns this session")
    title: str = Field(..., description="Session title")
    description: Optional[str] = Field(None, description="Session description")
    analysis_goal: Optional[str] = Field(None, description="Analysis goal/target for this session")
    message_count: int = Field(
        default=0,
        description="Total number of messages in this session",
    )
    is_active: bool = Field(
        default=True,
        description="Whether session is active",
    )
    created_at: datetime = Field(
        ...,
        description="Session creation timestamp (KST)",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp (KST)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 2,
                "title": "Drug Target Analysis - January 2026",
                "description": "Session for analyzing potential drug targets",
                "analysis_goal": "Focus on kinase inhibitor targets",
                "message_count": 15,
                "is_active": True,
                "created_at": "2026-01-17T10:30:00+09:00",
                "updated_at": "2026-01-17T15:45:00+09:00",
            }
        }


class SessionListResponse(BaseModel):
    """Response schema for session list with pagination."""

    sessions: list[SessionResponse] = Field(
        default=[],
        description="List of sessions",
    )
    total_count: int = Field(
        default=0,
        description="Total number of sessions for user",
    )
    limit: int = Field(..., description="Pagination limit")
    offset: int = Field(..., description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "sessions": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "user_123",
                        "title": "Session 1",
                        "message_count": 15,
                        "is_active": True,
                        "created_at": "2026-01-17T10:30:00+09:00",
                        "updated_at": "2026-01-17T15:45:00+09:00",
                    },
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "user_id": "user_123",
                        "title": "Session 2",
                        "message_count": 8,
                        "is_active": True,
                        "created_at": "2026-01-16T14:20:00+09:00",
                        "updated_at": "2026-01-16T20:10:00+09:00",
                    },
                ],
                "total_count": 2,
                "limit": 50,
                "offset": 0,
            }
        }


class SessionDeleteResponse(BaseModel):
    """Response schema for session deletion."""

    session_id: str = Field(..., description="Deleted session ID")
    success: bool = Field(..., description="Deletion success")
    deleted_message_count: int = Field(
        ...,
        description="Number of messages deleted with session",
    )
    timestamp: datetime = Field(
        ...,
        description="Deletion timestamp (KST)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "success": True,
                "deleted_message_count": 15,
                "timestamp": "2026-01-17T16:00:00+09:00",
            }
        }


class MessageResponse(BaseModel):
    """General response schema for simple messages."""

    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Operation success")
    timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp (KST)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully",
                "success": True,
                "timestamp": "2026-01-17T16:00:00+09:00",
            }
        }
