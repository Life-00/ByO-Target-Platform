"""
Analysis Agent API Routes

Endpoint:
- POST /api/v1/agents/analysis - Analyze documents with RAG and provide citations
"""

import logging
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analysis_agent import AnalysisAgent, AnalysisAgentRequest, AnalysisAgentResponse
from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.db.models import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["agents"])


@router.post(
    "",
    response_model=AnalysisAgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze documents with RAG and provide citations",
    responses={
        200: {"description": "Analysis completed successfully"},
        401: {"description": "Unauthorized"},
        500: {"description": "Analysis error"},
    },
)
async def analyze_documents(
    request: AnalysisAgentRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnalysisAgentResponse:
    """
    Analyze selected documents using RAG and provide evidence-based answers.

    This endpoint:
    1. Retrieves relevant chunks from ChromaDB based on selected documents
    2. Enriches chunks with page numbers from PostgreSQL
    3. Generates answer using LLM with citations
    4. Saves conversation to chat history

    Example:
    ```json
    {
        "user_id": 3,
        "session_id": 7,
        "content": "파킨슨병 환자의 보행 분석 방법은?",
        "analysis_goal": "치료 효과 평가 방법 이해",
        "selected_documents": [{"id": 12}, {"id": 15}],
        "top_k": 5,
        "min_relevance_score": 0.5
    }
    ```

    Returns analysis with precise citations (document, page, text excerpt).
    """
    try:
        logger.info(f"[AnalysisAPI] User {current_user['user_id']} analyzing: {request.content[:50]}...")

        # Save user message to DB
        user_message = ChatMessage(
            session_id=request.session_id,
            user_id=current_user['user_id'],
            role="user",
            content=request.content,
            created_at=datetime.now()
        )
        db.add(user_message)
        await db.flush()
        logger.info(f"[AnalysisAPI] Saved user message ID: {user_message.id}")

        # Execute analysis
        agent = AnalysisAgent(db=db)
        response = await agent.execute(request)

        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error or "Analysis failed"
            )

        # Save assistant message to DB
        assistant_message = ChatMessage(
            session_id=request.session_id,
            user_id=current_user['user_id'],
            role="assistant",
            content=response.answer,
            model_used="analysis_agent",
            tokens_used=response.tokens_used,
            created_at=datetime.now()
        )
        db.add(assistant_message)
        await db.commit()
        logger.info(f"[AnalysisAPI] Saved assistant message ID: {assistant_message.id}")

        return response

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"[AnalysisAPI] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
