"""
Chat service for managing conversations and LLM interactions.

Handles:
- Chat message storage and retrieval
- LLM integration via GeneralChatAgent
- Session management
- Token tracking and cost calculation
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.general_chat import GeneralChatAgent, ChatRequest
from app.config import settings
from app.db.models import ChatMessage, Session as DBSession
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat operations"""

    @staticmethod
    async def send_message(
        session: AsyncSession,
        user_id: str,
        session_id: int,
        content: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        selected_documents: Optional[list] = None,
        analysis_goal: Optional[str] = None,
    ) -> dict:
        """
        Send a message and get LLM response

        Args:
            session: Database session
            user_id: User ID
            session_id: Chat session ID
            content: User message content
            system_prompt: Optional system prompt override
            temperature: LLM temperature
            max_tokens: Maximum tokens in response
            selected_documents: List of selected documents for context
            analysis_goal: Analysis goal/target

        Returns:
            {
                "user_message_id": str,
                "assistant_message_id": str,
                "content": str,
                "usage": ChatLLMUsage dict,
                "finish_reason": str,
                "generated_at": datetime
            }

        Raises:
            ValueError: Invalid session
            LLMServiceError: LLM API error
        """
        # 세션 확인
        result = await session.execute(
            select(DBSession).where(
                and_(
                    DBSession.id == session_id,
                    DBSession.user_id == user_id,
                )
            )
        )
        db_session = result.scalars().first()

        if not db_session:
            raise ValueError(f"Session not found: {session_id}")

        # Debug logging
        logger.info(f"[ChatService] Received request:")
        logger.info(f"  - Content: {content[:100]}...")
        logger.info(f"  - Analysis Goal: {analysis_goal}")
        logger.info(f"  - Selected Documents Count: {len(selected_documents) if selected_documents else 0}")
        if selected_documents:
            logger.info(f"  - Selected Documents: {[doc.get('title') if isinstance(doc, dict) else doc.title for doc in selected_documents]}")

        # System prompt 생성 로직
        final_prompt = system_prompt
        if not final_prompt:
            logger.info("[ChatService] Using default prompt")
            final_prompt = """You are an expert AI research assistant specializing in academic papers.
Your task is to analyze, synthesize, and generate insights from scientific literature.
Be accurate, evidence-based, and cite your sources appropriately."""

        # 사용자 메시지 저장
        user_message = ChatMessage(
            session_id=int(session_id),
            user_id=user_id,
            role="user",
            content=content,
            tokens_used=_estimate_tokens(content),
            created_at=datetime.now(ZoneInfo("Asia/Seoul")),
        )
        session.add(user_message)
        await session.flush()

        # GeneralChatAgent 호출
        try:
            agent = GeneralChatAgent()
            
            # selected_documents를 dict로 변환 (Pydantic 모델이 이미 있는 경우)
            documents_dict = None
            if selected_documents:
                documents_dict = [
                    doc.dict() if hasattr(doc, 'dict') else doc
                    for doc in selected_documents
                ]
            
            request = ChatRequest(
                content=content,
                system_prompt=final_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                selected_documents=documents_dict,
                analysis_goal=analysis_goal,
            )
            agent_response = await agent.execute(request)
            
            logger.info(f"[ChatService] Response received: {len(agent_response.content)} chars")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"[ChatService] Agent 호출 실패: {str(e)}")
            raise

        # 어시스턴트 메시지 저장
        assistant_message = ChatMessage(
            session_id=int(session_id),
            user_id=user_id,
            role="assistant",
            content=agent_response.content,
            tokens_used=agent_response.tokens_used,
            created_at=datetime.now(ZoneInfo("Asia/Seoul")),
        )
        session.add(assistant_message)  # ✅ 누락된 add() 추가
        await session.commit()
        await session.refresh(assistant_message)  # ID 가져오기

        # 응답 형식
        estimated_cost = _estimate_cost(
            _estimate_tokens(content),
            agent_response.tokens_used,
        )

        return {
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id,
            "content": agent_response.content,
            "usage": {
                "prompt_tokens": _estimate_tokens(content),
                "completion_tokens": agent_response.tokens_used,
                "total_tokens": _estimate_tokens(content) + agent_response.tokens_used,
                "estimated_cost_usd": estimated_cost,
            },
            "finish_reason": "stop",
            "generated_at": assistant_message.created_at,
        }

    @staticmethod
    async def get_history(
        session: AsyncSession,
        user_id: str,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """
        Get chat history for a session

        Args:
            session: Database session
            user_id: User ID
            session_id: Chat session ID
            limit: Number of messages to retrieve
            offset: Pagination offset

        Returns:
            {
                "session_id": str,
                "messages": [ChatMessageResponse, ...],
                "total_count": int,
                "limit": int,
                "offset": int
            }
        """
        # 세션 확인
        result = await session.execute(
            select(DBSession).where(
                and_(
                    DBSession.id == int(session_id),
                    DBSession.user_id == user_id,
                )
            )
        )
        db_session = result.scalars().first()

        if not db_session:
            raise ValueError(f"Session not found: {session_id}")

        # 총 개수 조회
        count_result = await session.execute(
            select(ChatMessage).where(
                and_(
                    ChatMessage.session_id == int(session_id),
                    ChatMessage.user_id == user_id,
                )
            )
        )
        total_count = len(count_result.scalars().all())

        # 메시지 조회
        result = await session.execute(
            select(ChatMessage)
            .where(
                and_(
                    ChatMessage.session_id == int(session_id),
                    ChatMessage.user_id == user_id,
                )
            )
            .order_by(ChatMessage.created_at)
            .limit(limit)
            .offset(offset)
        )
        messages = result.scalars().all()

        return {
            "session_id": session_id,
            "messages": [
                {
                    "id": str(msg.id),
                    "session_id": str(msg.session_id),
                    "role": msg.role,
                    "content": msg.content,
                    "model_used": msg.model_used,
                    "token_count": msg.tokens_used or 0,
                    "created_at": msg.created_at,
                }
                for msg in messages
            ],
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    async def delete_message(
        session: AsyncSession,
        user_id: str,
        message_id: str,
    ) -> bool:
        """
        Delete a specific message

        Args:
            session: Database session
            user_id: User ID (ownership check)
            message_id: Message ID to delete

        Returns:
            True if deleted, False if not found
        """
        result = await session.execute(
            select(ChatMessage).where(
                and_(
                    ChatMessage.id == int(message_id),
                    ChatMessage.user_id == user_id,
                )
            )
        )
        message = result.scalars().first()

        if not message:
            return False

        await session.delete(message)
        await session.commit()
        return True

    @staticmethod
    async def clear_session(
        session: AsyncSession,
        user_id: str,
        session_id: str,
    ) -> int:
        """
        Clear all messages in a session

        Args:
            session: Database session
            user_id: User ID
            session_id: Session ID to clear

        Returns:
            Number of messages deleted
        """
        # 메시지 개수 확인
        result = await session.execute(
            select(ChatMessage).where(
                and_(
                    ChatMessage.session_id == int(session_id),
                    ChatMessage.user_id == user_id,
                )
            )
        )
        messages = result.scalars().all()
        count = len(messages)

        # 삭제
        for msg in messages:
            await session.delete(msg)

        await session.commit()
        return count


# ============================================================================
# Helper Functions
# ============================================================================


def _estimate_tokens(text: str) -> int:
    """
    Estimate token count from text

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    # 간단한 추정: 1 토큰 ≈ 4자
    return len(text) // 4 + 1


def _estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate API cost in USD

    Upstage Solar 1 Mini:
    - Input: $0.0004 / 1M tokens
    - Output: $0.0006 / 1M tokens

    Args:
        prompt_tokens: Input tokens
        completion_tokens: Output tokens

    Returns:
        Estimated cost in USD
    """
    input_cost = (prompt_tokens / 1_000_000) * 0.0004
    output_cost = (completion_tokens / 1_000_000) * 0.0006
    return input_cost + output_cost
