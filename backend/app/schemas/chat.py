"""
Pydantic schemas for chat-related API requests and responses.

These schemas provide:
- Chat message request/response validation
- Conversation history models
- LLM usage tracking
"""

from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas (Input)
# ============================================================================


class SelectedDocumentModel(BaseModel):
    """Model for selected document information"""
    id: int
    title: str
    summary: Optional[str] = None


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="Message content (1-8000 characters)",
    )
    session_id: int = Field(
        ...,
        description="Session ID to associate message with",
    )
    system_prompt: Optional[str] = Field(
        None,
        max_length=4000,
        description="Optional system prompt override",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM (0.0-2.0)",
    )
    max_tokens: int = Field(
        default=2048,
        ge=100,
        le=8192,
        description="Maximum tokens in response (100-8192)",
    )
    selected_documents: Optional[List[SelectedDocumentModel]] = Field(
        default=None,
        description="Selected documents for context",
    )
    analysis_goal: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Analysis goal or target",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "content": "What are the main challenges in target validation?",
                "session_id": "sess_abc123",
                "temperature": 0.7,
                "max_tokens": 2048,
                "selected_documents": [
                    {
                        "id": 1,
                        "title": "Paper 1",
                        "summary": "This paper discusses..."
                    }
                ],
                "analysis_goal": "Focus on limitations"
            }
        }


class ChatHistoryRequest(BaseModel):
    """Request schema for retrieving chat history."""

    session_id: str = Field(
        ...,
        description="Session ID to retrieve history for",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Number of messages to retrieve (1-500)",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Offset for pagination",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "limit": 50,
                "offset": 0,
            }
        }


class ChatClearRequest(BaseModel):
    """Request schema for clearing chat history."""

    session_id: str = Field(
        ...,
        description="Session ID to clear",
    )
    confirm: bool = Field(
        default=False,
        description="Confirmation to clear all messages",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "confirm": True,
            }
        }


# ============================================================================
# Response Schemas (Output)
# ============================================================================


class ChatMessageResponse(BaseModel):
    """Response schema for a single chat message."""

    id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Associated session ID")
    role: str = Field(
        ...,
        description="Message role (user or assistant)",
    )
    content: str = Field(..., description="Message content")
    token_count: int = Field(
        default=0,
        description="Token count for this message",
    )
    created_at: datetime = Field(
        ...,
        description="Message creation timestamp (KST)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_abc123",
                "session_id": "sess_abc123",
                "role": "user",
                "content": "What are the main challenges?",
                "token_count": 15,
                "created_at": "2026-01-17T10:30:00+09:00",
            }
        }


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""

    session_id: str = Field(..., description="Session ID")
    messages: list[ChatMessageResponse] = Field(
        default=[],
        description="List of messages in chronological order",
    )
    total_count: int = Field(
        default=0,
        description="Total message count in session",
    )
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "messages": [
                    {
                        "id": "msg_1",
                        "session_id": "sess_abc123",
                        "role": "user",
                        "content": "Hello",
                        "token_count": 5,
                        "created_at": "2026-01-17T10:00:00+09:00",
                    },
                    {
                        "id": "msg_2",
                        "session_id": "sess_abc123",
                        "role": "assistant",
                        "content": "Hi there!",
                        "token_count": 10,
                        "created_at": "2026-01-17T10:00:10+09:00",
                    },
                ],
                "total_count": 2,
                "limit": 50,
                "offset": 0,
            }
        }


class ChatLLMUsage(BaseModel):
    """LLM usage statistics for a response."""

    prompt_tokens: int = Field(..., description="Input tokens")
    completion_tokens: int = Field(..., description="Output tokens")
    total_tokens: int = Field(..., description="Total tokens")
    estimated_cost_usd: float = Field(
        ...,
        description="Estimated API cost in USD",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt_tokens": 150,
                "completion_tokens": 280,
                "total_tokens": 430,
                "estimated_cost_usd": 0.00034,
            }
        }


class ChatCompletionResponse(BaseModel):
    """Response schema for LLM completion."""

    message_id: str = Field(..., description="Message ID")
    content: str = Field(..., description="LLM response content")
    role: str = Field(default="assistant", description="Message role")
    usage: ChatLLMUsage = Field(..., description="Token usage statistics")
    finish_reason: str = Field(
        ...,
        description="Completion reason (stop, length, etc)",
    )
    generated_at: datetime = Field(
        ...,
        description="Generation timestamp (KST)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_abc123",
                "content": "Target validation involves...",
                "role": "assistant",
                "usage": {
                    "prompt_tokens": 150,
                    "completion_tokens": 280,
                    "total_tokens": 430,
                    "estimated_cost_usd": 0.00034,
                },
                "finish_reason": "stop",
                "generated_at": "2026-01-17T10:30:00+09:00",
            }
        }


class ChatErrorResponse(BaseModel):
    """Response schema for chat errors."""

    error: str = Field(..., description="Error type/message")
    detail: Optional[str] = Field(
        None,
        description="Detailed error information",
    )
    timestamp: datetime = Field(
        ...,
        description="Error timestamp (KST)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "LLMServiceError",
                "detail": "API rate limit exceeded",
                "timestamp": "2026-01-17T10:30:00+09:00",
            }
        }


class ChatDeleteResponse(BaseModel):
    """Response schema for message deletion."""

    message_id: str = Field(..., description="Deleted message ID")
    success: bool = Field(..., description="Deletion success")
    timestamp: datetime = Field(
        ...,
        description="Deletion timestamp (KST)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_abc123",
                "success": True,
                "timestamp": "2026-01-17T10:30:00+09:00",
            }
        }


class ChatClearResponse(BaseModel):
    """Response schema for clearing chat history."""

    session_id: str = Field(..., description="Session ID")
    deleted_count: int = Field(..., description="Number of messages deleted")
    timestamp: datetime = Field(
        ...,
        description="Clear operation timestamp (KST)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "deleted_count": 42,
                "timestamp": "2026-01-17T10:30:00+09:00",
            }
        }
