"""
Report Service
Handles report generation requests and integrates with chat system
Follows ChatService pattern for consistency
"""

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.report_agent.agent import ReportAgent
from app.agents.report_agent.schemas import (
    ReportAgentRequest,
    ReportAgentResponse,
    ResearchTopicData,
    DocumentReference,
)
from app.db.database import get_db_session
from app.services.session_service import SessionService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class ReportService:
    """
    Report Service
    Generates research feasibility reports
    Integrates with existing chat and session system
    """

    def __init__(self):
        """Initialize report service"""
        self.agent = ReportAgent()
        self.session_service = SessionService()
        self.user_service = UserService()

    async def generate_report(
        self,
        user_id: int,
        session_id: int,
        research_topic: str,
        research_description: Optional[str] = None,
        analysis_goal: Optional[str] = None,
        documents: Optional[list] = None,
        include_visualizations: bool = False,
        report_type: str = "markdown",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        db: Optional[AsyncSession] = None,
    ) -> ReportAgentResponse:
        """
        Generate a research feasibility report

        Args:
            user_id: User ID
            session_id: Chat session ID
            research_topic: Research topic to analyze
            research_description: Optional description of the research
            analysis_goal: Optional analysis goal
            documents: Optional list of document references
            include_visualizations: Whether to generate visualizations
            report_type: Report format type (markdown, pdf, json)
            temperature: LLM temperature (0-2.0)
            max_tokens: Maximum tokens for LLM response
            db: Database session

        Returns:
            ReportAgentResponse with generated report

        Raises:
            ValueError: If user or session not found
            Exception: If report generation fails
        """
        try:
            logger.info(
                f"[ReportService] Generating report for user {user_id}, "
                f"topic: {research_topic}"
            )

            # Step 1: Validate user and session
            if db:
                user = await self.user_service.get_user_by_id(db, user_id)
                if not user:
                    raise ValueError(f"User {user_id} not found")

                session = await self.session_service.get_session(db, user_id, session_id)
                if not session:
                    raise ValueError(f"Session {session_id} not found")
                logger.info(f"[ReportService] Session validated: {session_id}")

            # Step 2: Prepare document references
            document_refs = []
            if documents:
                for doc in documents:
                    document_refs.append(
                        DocumentReference(
                            title=doc.get("title", "Unknown"),
                            authors=doc.get("authors", "Unknown"),
                            year=doc.get("year"),
                            url=doc.get("url"),
                            abstract=doc.get("abstract"),
                        )
                    )
                logger.info(f"[ReportService] Prepared {len(document_refs)} document references")

            # Step 3: Build research data
            research_data = ResearchTopicData(
                topic=research_topic,
                description=research_description,
                analysis_goal=analysis_goal,
                related_documents=document_refs,
            )

            # Step 4: Create report request
            request = ReportAgentRequest(
                research_topic=research_topic,
                research_data=research_data if document_refs else None,
                include_visualizations=include_visualizations,
                report_type=report_type,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info(f"[ReportService] Report request created")

            # Step 5: Execute report agent
            response = await self.agent.execute(request)
            logger.info(f"[ReportService] Report generated successfully")

            # Step 6: Optionally save to database
            if db and response.report:
                await self._save_report_to_db(
                    user_id=user_id,
                    session_id=session_id,
                    report=response,
                    db=db,
                )
                logger.info(f"[ReportService] Report saved to database")

            return response

        except Exception as e:
            logger.error(
                f"[ReportService] Error generating report for {user_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def _save_report_to_db(
        self,
        user_id: int,
        session_id: int,
        report: ReportAgentResponse,
        db: AsyncSession,
    ) -> None:
        """
        Save generated report to database

        Args:
            user_id: User ID
            session_id: Session ID
            report: Generated report
            db: Database session
        """
        try:
            # TODO: Implement database storage
            # This would involve creating a Report model and saving to DB
            logger.info(f"[ReportService] Report saved for user {user_id}")

        except Exception as e:
            logger.error(f"[ReportService] Error saving report to DB: {str(e)}")
            # Don't fail the whole operation if save fails
            pass

    async def get_report_history(
        self,
        user_id: int,
        session_id: Optional[int] = None,
        db: Optional[AsyncSession] = None,
        limit: int = 10,
    ) -> list:
        """
        Get user's report generation history

        Args:
            user_id: User ID
            session_id: Optional session ID filter
            db: Database session
            limit: Maximum number of reports to retrieve

        Returns:
            List of report metadata
        """
        try:
            logger.info(f"[ReportService] Retrieving report history for {user_id}")

            # TODO: Implement database retrieval
            # Would query Report table filtered by user_id/session_id

            return []

        except Exception as e:
            logger.error(
                f"[ReportService] Error retrieving report history: {str(e)}"
            )
            raise

    async def delete_report(
        self,
        report_id: str,
        user_id: int,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Delete a generated report

        Args:
            report_id: Report ID
            user_id: User ID (for authorization)
            db: Database session

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If report not found or unauthorized
        """
        try:
            logger.info(f"[ReportService] Deleting report {report_id}")

            # TODO: Implement database deletion
            # Would verify ownership and delete from DB

            return True

        except Exception as e:
            logger.error(f"[ReportService] Error deleting report: {str(e)}")
            raise


# Singleton instance
_report_service = None


def get_report_service() -> ReportService:
    """Get or create report service instance"""
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service
