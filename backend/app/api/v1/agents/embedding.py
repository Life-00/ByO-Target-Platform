"""
Embedding Agent API Routes

Endpoints:
- POST /api/v1/agents/embedding - Embed documents (EmbeddingAgent)
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embedding_agent.agent import EmbeddingAgent
from app.agents.embedding_agent.schemas import EmbeddingAgentInputSchema
from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.db.models import Document
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embedding", tags=["agents"])


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Analyze PDF document",
    responses={
        200: {"description": "PDF analysis completed successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Document not found"},
        500: {"description": "Analysis service error"},
    },
)
async def analyze_pdf(
    request: dict,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    embedding_service: Annotated[EmbeddingService, Depends()],
):
    """
    Analyze a PDF document: extract text, chunk it, generate embeddings, and store in ChromaDB.

    Args:
        request: JSON body with document_id, session_id, and optional chunk_size
        db: Database session
        embedding_service: Service for generating and storing embeddings

    Returns:
        JSON response with analysis status and details
    """
    document_id = request.get("document_id")
    
    if not document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_id is required",
        )
    
    # Convert document_id to integer
    try:
        document_id = int(document_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_id must be a valid integer",
        )
    
    # Fetch document from database
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Initialize EmbeddingAgent
    agent = EmbeddingAgent(db, embedding_service)

    # Process the PDF using execute method
    request = EmbeddingAgentInputSchema(
        document_id=document_id,
        chunk_size=512
    )
    
    response = await agent.execute(request)

    return response
