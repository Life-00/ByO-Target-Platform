"""
Search Agent Schemas
Input and output data models for arXiv paper search agent
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SearchAgentRequest(BaseModel):
    """Input schema for search agent"""
    session_id: int = Field(..., description="Session ID for organizing downloaded papers")
    user_id: int = Field(..., description="User ID")
    content: str = Field(..., description="User's search query or question")
    analysis_goal: Optional[str] = Field(None, description="Specific analysis goal or research objective")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of papers to download")
    min_relevance_score: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum relevance score for filtering")
    selected_documents: Optional[List[Dict[str, Any]]] = Field(default=None, description="Already downloaded documents to exclude from download")


class PaperInfo(BaseModel):
    """Information about a searched paper"""
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    abstract: str = Field(..., description="Paper abstract")
    arxiv_id: str = Field(..., description="arXiv ID")
    pdf_url: str = Field(..., description="PDF download URL")
    published_date: str = Field(..., description="Publication date")
    relevance_score: float = Field(default=0.0, description="Relevance score (0-1)")


class SearchAgentResponse(BaseModel):
    """Output schema for search agent"""
    success: bool = Field(..., description="Whether search was successful")
    search_query: str = Field(..., description="Processed search query used")
    papers_found: int = Field(default=0, description="Total papers found")
    papers_filtered: int = Field(default=0, description="Papers after relevance filtering")
    papers_downloaded: int = Field(default=0, description="Papers successfully downloaded")
    papers: List[PaperInfo] = Field(default_factory=list, description="List of downloaded papers")
    download_paths: List[str] = Field(default_factory=list, description="Local file paths of downloaded PDFs")
    document_ids: List[int] = Field(default_factory=list, description="Database document IDs")
    error: Optional[str] = Field(None, description="Error message if any")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
