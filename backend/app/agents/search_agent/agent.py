"""
Search Agent Implementation (Orchestrator)

This agent orchestrates the paper search workflow:
1. Converting user query + analysis_goal into arXiv search query (using LLM)
2. Searching arXiv for relevant papers (delegated to arxiv_search.py)
3. Filtering papers by relevance (using LLM)
4. Downloading PDFs (delegated to pdf_download.py)
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.agents.search_agent.schemas import SearchAgentRequest, SearchAgentResponse, PaperInfo
from app.agents.search_agent.prompt import (
    SEARCH_QUERY_GENERATION_PROMPT,
    RELEVANCE_EVALUATION_PROMPT,
    REQUESTED_COUNT_EXTRACTION_PROMPT,
    DEFAULT_MAX_RESULTS,
)
from app.agents.search_agent.arxiv_search import search_arxiv
from app.agents.search_agent.pdf_download import download_pdfs
from app.services.llm_service import get_llm_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SearchAgent(BaseAgent):
    """
    Search Agent (Orchestrator)
    Coordinates arXiv paper search, relevance filtering, and PDF download
    """

    def __init__(self, db: AsyncSession = None):
        """Initialize search agent"""
        super().__init__()
        self.agent_type = "search_agent"
        self.llm_service = get_llm_service()
        self.db = db
        self.uploads_dir = Path("/app/uploads")  # Docker container path
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, request: SearchAgentRequest) -> SearchAgentResponse:
        """
        Execute paper search workflow
        
        Args:
            request: SearchAgentRequest with content and analysis_goal
            
        Returns:
            SearchAgentResponse with search results and downloaded papers
        """
        try:
            logger.info(f"[SearchAgent] Starting search: {request.content[:50]}...")

            # Step 0: Extract requested paper count using LLM
            actual_max_results = await self._extract_requested_count(request.content)
            logger.info(f"[SearchAgent] Requested count from LLM: {actual_max_results}")

            # Step 0.5: Extract already downloaded arxiv IDs from selected_documents
            existing_arxiv_ids = set()
            if request.selected_documents:
                for doc in request.selected_documents:
                    # Extract arxiv ID from description field (e.g., "arXiv 2212.00109")
                    description = doc.get('description', '')
                    if 'arXiv' in description:
                        arxiv_id = description.split('arXiv')[1].strip().split()[0].split('-')[0]
                        existing_arxiv_ids.add(arxiv_id)
                logger.info(f"[SearchAgent] Found {len(existing_arxiv_ids)} existing papers to skip: {existing_arxiv_ids}")

            # Step 1: Generate arXiv search query from user input
            search_query = await self._generate_search_query(
                request.content, 
                request.analysis_goal
            )
            logger.info(f"[SearchAgent] Generated search query: {search_query}")

            # Step 2: Search arXiv (delegated to arxiv_search module)
            papers = await search_arxiv(search_query, actual_max_results * 4)
            logger.info(f"[SearchAgent] Found {len(papers)} papers from arXiv")

            if not papers:
                return SearchAgentResponse(
                    success=True,
                    search_query=search_query,
                    papers_found=0,
                    papers_filtered=0,
                    papers_downloaded=0,
                    papers=[],
                    download_paths=[],
                    document_ids=[],
                    metadata={"message": "No papers found for this query"}
                )

            # Step 3: Filter by relevance
            filtered_papers = await self._filter_by_relevance(
                papers,
                request.content,
                request.analysis_goal,
                request.min_relevance_score,
                actual_max_results,
                existing_arxiv_ids  # Pass existing IDs to skip
            )
            logger.info(f"[SearchAgent] Filtered to {len(filtered_papers)} relevant papers (excluding duplicates)")

            # Step 4: Download PDFs and register in DB (delegated to pdf_download module)
            download_results = await download_pdfs(
                filtered_papers,
                request.session_id,
                request.user_id,
                self.uploads_dir,
                self.db
            )
            logger.info(f"[SearchAgent] Downloaded {len(download_results['paths'])} PDFs")

            return SearchAgentResponse(
                success=True,
                search_query=search_query,
                papers_found=len(papers),
                papers_filtered=len(filtered_papers),
                papers_downloaded=len(download_results['paths']),
                papers=filtered_papers,
                download_paths=download_results['paths'],
                document_ids=download_results['document_ids'],
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "min_relevance": request.min_relevance_score,
                    "requested_count": actual_max_results,
                    "excluded_duplicates": len(existing_arxiv_ids)
                }
            )

        except Exception as e:
            logger.error(f"[SearchAgent] Error: {str(e)}")
            return SearchAgentResponse(
                success=False,
                search_query="",
                papers_found=0,
                papers_filtered=0,
                papers_downloaded=0,
                papers=[],
                download_paths=[],
                error=str(e)
            )

    async def _extract_requested_count(self, content: str) -> int:
        """
        Step 0: Extract how many papers user wants using LLM
        """
        try:
            prompt = REQUESTED_COUNT_EXTRACTION_PROMPT.format(content=content)

            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert at understanding user requests.",
                temperature=0.1,
                max_tokens=50
            )

            # Parse JSON response
            result = json.loads(response["content"].strip())
            requested_count = int(result.get("requested_count", DEFAULT_MAX_RESULTS))
            
            # Clamp between 1 and 20
            requested_count = max(1, min(20, requested_count))
            
            return requested_count

        except Exception as e:
            logger.warning(f"[SearchAgent] Count extraction failed: {str(e)}, using default")
            return DEFAULT_MAX_RESULTS

    async def _generate_search_query(self, content: str, analysis_goal: Optional[str]) -> str:
        """
        Step 1: Convert user query + analysis_goal into arXiv search query using LLM
        """
        try:
            prompt = SEARCH_QUERY_GENERATION_PROMPT.format(
                content=content,
                analysis_goal=analysis_goal or "General research"
            )

            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert research assistant.",
                temperature=0.3,
                max_tokens=100
            )

            query = response["content"].strip()
            return query

        except Exception as e:
            logger.error(f"[SearchAgent] Query generation failed: {str(e)}")
            # Fallback: use original content
            return content[:100]

    async def _filter_by_relevance(
        self,
        papers: List[Dict[str, Any]],
        content: str,
        analysis_goal: Optional[str],
        min_score: float,
        max_results: int,
        existing_arxiv_ids: set = None
    ) -> List[PaperInfo]:
        """
        Step 3: Filter papers by relevance using LLM to compare abstracts
        Also skip papers that are already downloaded (in existing_arxiv_ids)
        """
        if existing_arxiv_ids is None:
            existing_arxiv_ids = set()
            
        filtered = []

        for paper in papers:
            try:
                # Skip if already downloaded
                if paper["arxiv_id"] in existing_arxiv_ids:
                    logger.info(f"[SearchAgent] Skipping duplicate: {paper['arxiv_id']}")
                    continue

                # Evaluate relevance using LLM
                prompt = RELEVANCE_EVALUATION_PROMPT.format(
                    content=content,
                    analysis_goal=analysis_goal or "General research",
                    title=paper["title"],
                    abstract=paper["abstract"][:1000]  # Truncate long abstracts
                )

                response = await self.llm_service.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are an expert at evaluating research paper relevance.",
                    temperature=0.3,
                    max_tokens=200
                )

                # Parse JSON response
                result = json.loads(response["content"].strip())
                relevance_score = float(result.get("relevance_score", 0.0))

                logger.info(f"[SearchAgent] '{paper['title'][:50]}...' - Relevance: {relevance_score:.2f}")

                if relevance_score >= min_score:
                    filtered.append(PaperInfo(
                        title=paper["title"],
                        authors=paper["authors"],
                        abstract=paper["abstract"],
                        arxiv_id=paper["arxiv_id"],
                        pdf_url=paper["pdf_url"],
                        published_date=paper["published_date"],
                        relevance_score=relevance_score
                    ))

                    if len(filtered) >= max_results:
                        break

            except Exception as e:
                logger.warning(f"[SearchAgent] Relevance check failed for paper: {str(e)}")
                continue

        # Sort by relevance score
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)
        return filtered[:max_results]
