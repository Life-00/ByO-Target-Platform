"""
API endpoints for session management.

Provides:
- POST /api/v1/sessions - Create new session
- GET /api/v1/sessions - List user's sessions
- GET /api/v1/sessions/{session_id} - Get session details
- PUT /api/v1/sessions/{session_id} - Update session
- DELETE /api/v1/sessions/{session_id} - Delete session
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.schemas.session import (
    MessageResponse,
    SessionCreateRequest,
    SessionDeleteResponse,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
    SessionUpdateRequest,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=201,
    summary="Create new session",
    responses={
        201: {"description": "Session created successfully"},
        401: {"description": "Unauthorized"},
        422: {"description": "Invalid request"},
    },
)
async def create_session(
    request: SessionCreateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionResponse:
    """
    Create a new chat session.

    **Required:**
    - title: Session title (1-255 characters)

    **Optional:**
    - description: Session description (up to 1000 characters)

    **Returns:**
    - Created SessionResponse with session details
    """
    return await SessionService.create_session(
        db=db,
        user_id=current_user["user_id"],
        request=request,
    )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List user's sessions",
    responses={
        200: {"description": "Sessions retrieved"},
        401: {"description": "Unauthorized"},
    },
)
async def list_sessions(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=500, description="Max 500")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> SessionListResponse:
    """
    Get list of user's sessions with pagination.

    **Query Parameters:**
    - limit: Number of sessions to return (1-500, default 50)
    - offset: Number of sessions to skip (default 0)

    **Returns:**
    - SessionListResponse with sessions and total count
    """
    sessions, total_count = await SessionService.list_sessions(
        db=db,
        user_id=current_user["user_id"],
        limit=limit,
        offset=offset,
    )

    return SessionListResponse(
        sessions=sessions,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session details",
    responses={
        200: {"description": "Session found"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
    },
)
async def get_session(
    session_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionResponse:
    """
    Get a specific session by ID.

    **Path Parameters:**
    - session_id: ID of the session

    **Returns:**
    - SessionResponse with session details or 404 if not found
    """
    session = await SessionService.get_session(
        db=db,
        user_id=current_user["user_id"],
        session_id=session_id,
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    return session


@router.put(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Update session",
    responses={
        200: {"description": "Session updated"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        422: {"description": "Invalid request"},
    },
)
async def update_session(
    session_id: int,
    request: SessionUpdateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionResponse:
    """
    Update session metadata.

    **Path Parameters:**
    - session_id: ID of the session

    **Body Parameters:**
    - title: New session title (optional)
    - description: New session description (optional)

    **Returns:**
    - Updated SessionResponse or 404 if not found
    """
    session = await SessionService.update_session(
        db=db,
        user_id=current_user["user_id"],
        session_id=session_id,
        request=request,
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    return session


@router.put(
    "/{session_id}/goal",
    response_model=SessionResponse,
    summary="Update analysis goal",
    responses={
        200: {"description": "Analysis goal updated"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        422: {"description": "Invalid request"},
    },
)
async def update_analysis_goal(
    session_id: int,
    request: SessionUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionResponse:
    """
    Update session analysis goal.

    **Path Parameters:**
    - session_id: ID of the session

    **Body Parameters:**
    - analysis_goal: New analysis goal/target (optional)

    **Returns:**
    - Updated SessionResponse or 404 if not found
    """
    session = await SessionService.update_analysis_goal(
        db=db,
        user_id=current_user["user_id"],
        session_id=session_id,
        request=request,
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    return session


@router.delete(
    "/{session_id}",
    response_model=SessionDeleteResponse,
    summary="Delete session",
    responses={
        200: {"description": "Session deleted"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
    },
)
async def delete_session(
    session_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionDeleteResponse:
    """
    Delete a session and all its messages.

    **Path Parameters:**
    - session_id: ID of the session to delete

    **Returns:**
    - SessionDeleteResponse with deletion details or 404 if not found

    **Warning:**
    - This is permanent and will delete all messages in the session
    """
    result = await SessionService.delete_session(
        db=db,
        user_id=current_user["user_id"],
        session_id=session_id,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    return result
