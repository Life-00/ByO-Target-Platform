"""
Report API Router
Handles API endpoints for report generation
"""

import logging
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.agents.report_agent.schemas import (
    ReportAgentRequest,
    ReportAgentResponse,
)
from app.services.report_service import get_report_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/report",
    tags=["report_agent"],
)

# ============================================================================
# Report Generation Endpoints
# ============================================================================


@router.post("/generate", response_model=ReportAgentResponse)
async def generate_report(
    request: ReportAgentRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session_id: Optional[str] = Query(None),
) -> ReportAgentResponse:
    """
    Generate a research feasibility report

    Args:
        request: Report generation request with research topic and optional parameters
        current_user: Authenticated user
        session_id: Optional chat session ID
        db: Database session

    Returns:
        ReportAgentResponse with generated report and metadata

    Raises:
        HTTPException: If generation fails
    """
    try:
        user_id = current_user["user_id"]
        logger.info(
            f"[ReportRouter] Report generation request from user {user_id}, "
            f"topic: {request.research_topic}"
        )

        report_service = get_report_service()

        # Generate report
        session_id_int = int(session_id) if session_id else user_id
        
        response = await report_service.generate_report(
            user_id=user_id,
            session_id=session_id_int,
            research_topic=request.research_topic,
            research_description=request.research_data.description if request.research_data else None,
            analysis_goal=request.research_data.analysis_goal if request.research_data else None,
            documents=[doc.dict() for doc in request.research_data.related_documents]
                if request.research_data and request.research_data.related_documents else None,
            include_visualizations=request.include_visualizations,
            report_type=request.report_type,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            db=db,
        )

        logger.info(f"[ReportRouter] Report generated successfully")
        return response

    except ValueError as e:
        logger.error(f"[ReportRouter] Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ReportRouter] Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate report. Please try again later.",
        )


@router.get("/history")
async def get_report_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    session_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get user's report generation history

    Args:
        current_user: Authenticated user
        session_id: Optional session ID filter
        limit: Maximum number of reports to retrieve (1-100)
        db: Database session

    Returns:
        List of report metadata

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        user_id = current_user["user_id"]
        logger.info(
            f"[ReportRouter] Retrieving report history for user {user_id}"
        )

        report_service = get_report_service()

        history = await report_service.get_report_history(
            user_id=user_id,
            session_id=int(session_id) if session_id else None,
            db=db,
            limit=limit,
        )

        return {
            "user_id": user_id,
            "history": history,
            "count": len(history),
        }

    except Exception as e:
        logger.error(
            f"[ReportRouter] Error retrieving report history: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve report history.",
        )


@router.delete("/delete/{report_id}")
async def delete_report(
    report_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Delete a generated report

    Args:
        report_id: Report ID to delete
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If deletion fails or unauthorized
    """
    try:
        user_id = current_user["user_id"]
        logger.info(
            f"[ReportRouter] Delete report request from user {user_id}, "
            f"report_id: {report_id}"
        )

        report_service = get_report_service()

        success = await report_service.delete_report(
            report_id=report_id,
            user_id=user_id,
            db=db,
        )

        return {
            "success": success,
            "report_id": report_id,
            "message": "Report deleted successfully",
        }

    except ValueError as e:
        logger.error(f"[ReportRouter] Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"[ReportRouter] Error deleting report: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to delete report.",
        )


@router.get("/download/{report_id}")
async def download_report(
    report_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    format: str = Query("markdown", pattern="^(markdown|pdf|json)$"),
) -> dict:
    """
    Download a generated report in specified format

    Args:
        report_id: Report ID to download
        format: Download format (markdown, pdf, json)
        current_user: Authenticated user
        db: Database session

    Returns:
        Report content with appropriate media type

    Raises:
        HTTPException: If download fails or unauthorized
    """
    try:
        user_id = current_user["user_id"]
        logger.info(
            f"[ReportRouter] Download report request from user {user_id}, "
            f"report_id: {report_id}, format: {format}"
        )

        report_service = get_report_service()

        # TODO: Implement report download
        # Would retrieve report from database and return in requested format

        return {
            "report_id": report_id,
            "format": format,
            "url": f"/downloads/{report_id}.{format}",
            "message": "Download link generated",
        }

    except ValueError as e:
        logger.error(f"[ReportRouter] Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"[ReportRouter] Error downloading report: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to download report.",
        )


# ============================================================================
# Analysis Endpoints
# ============================================================================


@router.post("/analyze")
async def quick_analysis(
    topic: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Quick analysis without full report generation
    Useful for quick topic feasibility assessment

    Args:
        topic: Research topic to analyze
        current_user: Authenticated user
        db: Database session

    Returns:
        Quick analysis result

    Raises:
        HTTPException: If analysis fails
    """
    try:
        user_id = current_user["user_id"]
        logger.info(
            f"[ReportRouter] Quick analysis request from user {user_id}, "
            f"topic: {topic}"
        )

        report_service = get_report_service()

        response = await report_service.generate_report(
            user_id=user_id,
            session_id=user_id,
            research_topic=topic,
            documents=None,
            include_visualizations=False,
            report_type="json",
            db=db,
        )

        return {
            "topic": topic,
            "analysis": response.report.validation.reasoning,
            "feasibility_score": response.report.validation.feasibility_score,
            "is_feasible": response.report.validation.is_feasible,
        }

    except Exception as e:
        logger.error(
            f"[ReportRouter] Error in quick analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to perform analysis.",
        )


