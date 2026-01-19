"""
Business logic for session management.

SessionService handles:
- Creating and retrieving sessions
- Updating session metadata
- Deleting sessions and their associated messages
- Listing user's sessions with pagination
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatMessage, Session
from app.schemas.session import (
    SessionCreateRequest,
    SessionDeleteResponse,
    SessionResponse,
    SessionUpdate,
    SessionUpdateRequest,
)

KST = ZoneInfo("Asia/Seoul")


class SessionService:
    """Service for managing chat sessions."""

    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: int,
        request: SessionCreateRequest,
    ) -> SessionResponse:
        """
        Create a new session for user.

        Args:
            db: AsyncSession database connection
            user_id: User ID who owns the session
            request: SessionCreateRequest with title and description

        Returns:
            SessionResponse with created session details
        """
        session = Session(
            user_id=user_id,
            title=request.title,
            description=request.description,
            is_active=True,
        )

        db.add(session)
        await db.flush()  # Flush to get the ID
        await db.commit()

        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            description=session.description,
            analysis_goal=session.analysis_goal,
            message_count=0,
            is_active=session.is_active,
            created_at=session.created_at.replace(tzinfo=KST),
            updated_at=session.updated_at.replace(tzinfo=KST),
        )

    @staticmethod
    async def get_session(
        db: AsyncSession,
        user_id: int,
        session_id: int,
    ) -> SessionResponse | None:
        """
        Get a specific session by ID.

        Args:
            db: AsyncSession database connection
            user_id: User ID (for authorization check)
            session_id: Session ID to retrieve

        Returns:
            SessionResponse or None if not found
        """
        # Get session with message count
        query = (
            select(Session)
            .where(
                (Session.id == session_id)
                & (Session.user_id == user_id)
            )
        )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Count messages
        count_query = select(func.count(ChatMessage.id)).where(
            ChatMessage.session_id == session_id
        )
        count_result = await db.execute(count_query)
        message_count = count_result.scalar() or 0

        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            description=session.description,
            analysis_goal=session.analysis_goal,
            message_count=message_count,
            is_active=session.is_active,
            created_at=session.created_at.replace(tzinfo=KST),
            updated_at=session.updated_at.replace(tzinfo=KST),
        )

    @staticmethod
    async def list_sessions(
        db: AsyncSession,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[SessionResponse], int]:
        """
        List user's sessions with pagination.

        Args:
            db: AsyncSession database connection
            user_id: User ID to filter sessions
            limit: Maximum number of sessions (default 50, max 500)
            offset: Number of sessions to skip

        Returns:
            Tuple of (SessionResponse list, total count)
        """
        # Clamp limit
        limit = min(max(limit, 1), 500)

        # Get total count
        count_query = select(func.count(Session.id)).where(
            Session.user_id == user_id
        )
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get sessions ordered by created_at descending
        query = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(desc(Session.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        sessions = result.scalars().all()

        # Build response with message counts
        responses = []
        for session in sessions:
            count_query = select(func.count(ChatMessage.id)).where(
                ChatMessage.session_id == session.id
            )
            count_result = await db.execute(count_query)
            message_count = count_result.scalar() or 0

            responses.append(
                SessionResponse(
                    id=session.id,
                    user_id=session.user_id,
                    title=session.title,
                    description=session.description,
                    analysis_goal=session.analysis_goal,
                    message_count=message_count,
                    is_active=session.is_active,
                    created_at=session.created_at.replace(tzinfo=KST),
                    updated_at=session.updated_at.replace(tzinfo=KST),
                )
            )

        return responses, total_count

    @staticmethod
    async def update_session(
        db: AsyncSession,
        user_id: int,
        session_id: int,
        request: SessionUpdateRequest,
    ) -> SessionResponse | None:
        """
        Update session metadata (title, description).

        Args:
            db: AsyncSession database connection
            user_id: User ID (for authorization)
            session_id: Session ID to update
            request: SessionUpdateRequest with new data

        Returns:
            Updated SessionResponse or None if not found
        """
        query = select(Session).where(
            (Session.id == session_id) & (Session.user_id == user_id)
        )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Update fields if provided
        if request.title is not None:
            session.title = request.title
        if request.description is not None:
            session.description = request.description

        await db.commit()

        # Count messages
        count_query = select(func.count(ChatMessage.id)).where(
            ChatMessage.session_id == session_id
        )
        count_result = await db.execute(count_query)
        message_count = count_result.scalar() or 0

        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            description=session.description,
            analysis_goal=session.analysis_goal,
            message_count=message_count,
            is_active=session.is_active,
            created_at=session.created_at.replace(tzinfo=KST),
            updated_at=session.updated_at.replace(tzinfo=KST),
        )

    @staticmethod
    async def update_analysis_goal(
        db: AsyncSession,
        user_id: int,
        session_id: int,
        request: SessionUpdate,
    ) -> SessionResponse | None:
        """
        Update session analysis goal.

        Args:
            db: AsyncSession database connection
            user_id: User ID (for authorization)
            session_id: Session ID to update
            request: SessionUpdate with analysis_goal

        Returns:
            Updated SessionResponse or None if not found
        """
        query = select(Session).where(
            (Session.id == session_id) & (Session.user_id == user_id)
        )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Update analysis_goal if provided
        if request.analysis_goal is not None:
            session.analysis_goal = request.analysis_goal

        await db.commit()

        # Count messages
        count_query = select(func.count(ChatMessage.id)).where(
            ChatMessage.session_id == session_id
        )
        count_result = await db.execute(count_query)
        message_count = count_result.scalar() or 0

        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            description=session.description,
            analysis_goal=session.analysis_goal,
            message_count=message_count,
            is_active=session.is_active,
            created_at=session.created_at.replace(tzinfo=KST),
            updated_at=session.updated_at.replace(tzinfo=KST),
        )

    @staticmethod
    async def delete_session(
        db: AsyncSession,
        user_id: int,
        session_id: int,
    ) -> SessionDeleteResponse | None:
        """
        Delete a session and all its messages.

        Args:
            db: AsyncSession database connection
            user_id: User ID (for authorization)
            session_id: Session ID to delete

        Returns:
            SessionDeleteResponse with deletion details or None if not found
        """
        # Get session (authorization check)
        query = select(Session).where(
            (Session.id == session_id) & (Session.user_id == user_id)
        )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Count messages before deletion
        count_query = select(func.count(ChatMessage.id)).where(
            ChatMessage.session_id == session_id
        )
        count_result = await db.execute(count_query)
        message_count = count_result.scalar() or 0

        # Delete messages
        delete_msg_query = ChatMessage.__table__.delete().where(
            ChatMessage.session_id == session_id
        )
        await db.execute(delete_msg_query)

        # Delete session
        await db.delete(session)
        await db.commit()

        return SessionDeleteResponse(
            session_id=str(session_id),
            success=True,
            deleted_message_count=message_count,
            timestamp=datetime.now(KST),
        )
