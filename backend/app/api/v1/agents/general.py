"""
General Chat Agent API Routes

Endpoints:
- POST /api/v1/agents/general/message - Send message and get LLM response
- GET /api/v1/agents/general/history - Get chat history
- DELETE /api/v1/agents/general/{message_id} - Delete message
- DELETE /api/v1/agents/general/session/{session_id} - Clear session
"""

import logging
from datetime import datetime
from typing import Annotated, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.schemas.chat import (
    ChatClearRequest,
    ChatClearResponse,
    ChatCompletionResponse,
    ChatDeleteResponse,
    ChatErrorResponse,
    ChatHistoryRequest,
    ChatHistoryResponse,
    ChatLLMUsage,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.services.chat_service import ChatService
from app.services.llm_service import LLMServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/general", tags=["agents"])


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/message",
    response_model=ChatCompletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Send chat message and get LLM response",
    responses={
        200: {"description": "LLM response generated successfully"},
        400: {"description": "Invalid request (bad message content)", "model": ChatErrorResponse},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found", "model": ChatErrorResponse},
        500: {"description": "LLM API error", "model": ChatErrorResponse},
    },
)
async def send_message(
    request: ChatMessageRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatCompletionResponse:
    """
    Send a message to the default LLM and get response.

    This endpoint:
    1. Validates the message content
    2. Stores the user message in database
    3. Calls Upstage LLM API (solar-1-mini-chat) via GeneralChatAgent
    4. Stores the assistant response
    5. Returns the response with token usage

    Query parameters:
    - temperature: 0.0-2.0 (default: 0.7) - Control randomness
    - max_tokens: 100-8192 (default: 2048) - Limit response length

    Example:
    ```json
    {
        "content": "What are the main challenges in target validation?",
        "session_id": "sess_abc123",
        "temperature": 0.7,
        "max_tokens": 2048
    }
    ```

    Returns the assistant's response with token usage stats and estimated cost.
    """
    try:
        # 메시지 전송
        result = await ChatService.send_message(
            session=db,
            user_id=current_user["user_id"],
            session_id=request.session_id,
            content=request.content,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            selected_documents=request.selected_documents,
            analysis_goal=request.analysis_goal,
        )

        # 응답 형식
        return ChatCompletionResponse(
            message_id=str(result["assistant_message_id"]),
            content=result["content"],
            role="assistant",
            usage=ChatLLMUsage(
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                total_tokens=result["usage"]["total_tokens"],
                estimated_cost_usd=result["usage"]["estimated_cost_usd"],
            ),
            finish_reason=result["finish_reason"],
            generated_at=result["generated_at"],
        )

    except ValueError as e:
        # 세션 없음
        logger.warning(f"세션 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except LLMServiceError as e:
        # LLM API 에러
        logger.error(f"LLM 서비스 에러: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM API error: {str(e)}",
        )

    except Exception as e:
        # 예상치 못한 에러
        logger.error(f"메시지 전송 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chat history for a session",
    responses={
        200: {"description": "Chat history retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found", "model": ChatErrorResponse},
    },
)
async def get_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session_id: str = Query(..., description="Session ID"),
    limit: Annotated[int, Query(ge=1, le=500, description="Max 500")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> ChatHistoryResponse:
    """
    Retrieve chat history for a specific session.

    Query parameters:
    - session_id: Session ID to retrieve history for
    - limit: Number of messages to retrieve (default: 50, max: 500)
    - offset: Pagination offset (default: 0)

    Returns paginated chat history with message details.
    """
    try:
        result = await ChatService.get_history(
            session=db,
            user_id=current_user["user_id"],
            session_id=session_id,
            limit=min(limit, 500),  # Cap at 500
            offset=max(offset, 0),
        )

        return ChatHistoryResponse(
            session_id=result["session_id"],
            messages=[
                ChatMessageResponse(
                    id=msg["id"],
                    session_id=msg["session_id"],
                    role=msg["role"],
                    content=msg["content"],
                    token_count=msg["token_count"],
                    created_at=msg["created_at"],
                )
                for msg in result["messages"]
            ],
            total_count=result["total_count"],
            limit=result["limit"],
            offset=result["offset"],
        )

    except ValueError as e:
        logger.warning(f"세션 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"히스토리 조회 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete(
    "/{message_id}",
    response_model=ChatDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a specific chat message",
    responses={
        200: {"description": "Message deleted successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Message not found", "model": ChatErrorResponse},
    },
)
async def delete_message(
    message_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatDeleteResponse:
    """
    Delete a specific message from chat history.

    Note: Only the message owner (original user) can delete messages.
    """
    try:
        deleted = await ChatService.delete_message(
            session=db,
            user_id=current_user["user_id"],
            message_id=message_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        return ChatDeleteResponse(
            message_id=message_id,
            success=True,
            timestamp=datetime.now(ZoneInfo("Asia/Seoul")),
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"메시지 삭제 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete(
    "/session/{session_id}/clear",
    response_model=ChatClearResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear all messages in a session",
    responses={
        200: {"description": "Session cleared successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found", "model": ChatErrorResponse},
    },
)
async def clear_session(
    session_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatClearResponse:
    """
    Clear all messages from a chat session.

    Warning: This action cannot be undone. All messages in the session will be deleted.
    """
    try:
        deleted_count = await ChatService.clear_session(
            session=db,
            user_id=current_user["user_id"],
            session_id=session_id,
        )

        return ChatClearResponse(
            session_id=session_id,
            deleted_count=deleted_count,
            timestamp=datetime.now(ZoneInfo("Asia/Seoul")),
        )

    except Exception as e:
        logger.error(f"세션 삭제 에러: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# ============================================================================
# Health Check
# ============================================================================


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Chat service health check",
)
async def health_check() -> dict:
    """
    Check if chat service is operational.

    Returns basic status information.
    """
    return {
        "status": "healthy",
        "service": "general_chat",
        "timestamp": datetime.now(ZoneInfo("Asia/Seoul")),
    }
