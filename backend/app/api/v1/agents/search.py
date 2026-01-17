"""
Search Agent API Routes

Endpoint:
- POST /api/v1/agents/search - Search arXiv papers and download PDFs
"""

import logging
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.search_agent import SearchAgent, SearchAgentRequest, SearchAgentResponse
from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.db.models import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["agents"])


@router.post(
    "",
    response_model=SearchAgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Search arXiv papers and download PDFs",
    responses={
        200: {"description": "Papers searched and downloaded successfully"},
        401: {"description": "Unauthorized"},
        500: {"description": "Search or download error"},
    },
)
async def search_papers(
    request: SearchAgentRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SearchAgentResponse:
    """
    Search arXiv for relevant papers and download PDFs.

    This endpoint:
    1. Converts user query + analysis_goal into arXiv search query (using LLM)
    2. Searches arXiv API for papers
    3. Filters papers by relevance (comparing abstracts with user intent using LLM)
    4. Downloads relevant PDFs to /uploads/{session_id}/ directory
    5. Registers downloaded papers in database

    Example:
    ```json
    {
        "session_id": 7,
        "user_id": 3,
        "content": "What are the latest advances in transformer models?",
        "analysis_goal": "Understanding attention mechanisms",
        "max_results": 5,
        "min_relevance_score": 0.7
    }
    ```

    Returns list of papers with relevance scores, local PDF paths, and document IDs.
    """
    try:
        logger.info(f"[SearchAPI] User {current_user['user_id']} searching: {request.content[:50]}...")

        # Save user message to DB
        user_message = ChatMessage(
            session_id=request.session_id,
            user_id=current_user['user_id'],
            role="user",
            content=request.content,
            created_at=datetime.now()
        )
        db.add(user_message)
        await db.flush()  # Get message ID
        logger.info(f"[SearchAPI] Saved user message ID: {user_message.id}")

        # Execute search
        agent = SearchAgent(db=db)
        response = await agent.execute(request)

        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error or "Search failed"
            )

        # Format assistant response
        result_content = f"🔍 **검색 결과**\n\n"
        result_content += f"- 검색어: {response.search_query}\n"
        result_content += f"- 발견: {response.papers_found}개 → 필터링: {response.papers_filtered}개 → 다운로드: {response.papers_downloaded}개\n\n"

        if response.papers and len(response.papers) > 0:
            result_content += f"**다운로드된 논문:**\n\n"
            for idx, paper in enumerate(response.papers, 1):
                result_content += f"{idx}. **{paper.title}**\n"
                result_content += f"   - 저자: {', '.join(paper.authors[:3])}"
                if len(paper.authors) > 3:
                    result_content += " 외"
                result_content += f"\n   - 관련성: {paper.relevance_score * 100:.0f}%\n"
                result_content += f"   - arXiv ID: {paper.arxiv_id}\n\n"
        else:
            result_content += "검색 결과가 없습니다."

        # Save assistant message to DB
        assistant_message = ChatMessage(
            session_id=request.session_id,
            user_id=current_user['user_id'],
            role="assistant",
            content=result_content,
            model_used="search_agent",
            created_at=datetime.now()
        )
        db.add(assistant_message)
        await db.commit()
        logger.info(f"[SearchAPI] Saved assistant message ID: {assistant_message.id}")

        return response

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"[SearchAPI] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
