"""
Analysis Agent Schemas
Input and output data models for document analysis with RAG
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AnalysisAgentRequest(BaseModel):
    """Input schema for analysis agent"""
    user_id: int = Field(..., description="User ID")
    session_id: int = Field(..., description="Session ID")
    content: str = Field(..., description="User's question or analysis request")
    analysis_goal: Optional[str] = Field(None, description="Specific analysis objective")
    selected_documents: List[Dict[str, Any]] = Field(..., description="Documents to analyze (must have 'id' field)")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    min_relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum relevance threshold")


class CitationInfo(BaseModel):
    """Information about a citation/source"""
    document_id: int = Field(..., description="Document ID")
    document_title: str = Field(..., description="Document title")
    filename: str = Field(..., description="Original filename")
    chunk_index: int = Field(..., description="Chunk index within document")
    text_excerpt: str = Field(..., description="Relevant text excerpt")
    relevance_score: float = Field(..., description="Relevance score (0-1)")


class AnalysisAgentResponse(BaseModel):
    """Output schema for analysis agent"""
    success: bool = Field(..., description="Whether analysis was successful")
    answer: str = Field(..., description="Generated answer in Korean with citations")
    citations: List[CitationInfo] = Field(default_factory=list, description="List of evidence sources")
    documents_analyzed: int = Field(default=0, description="Number of documents analyzed")
    chunks_retrieved: int = Field(default=0, description="Number of chunks retrieved from vector DB")
    tokens_used: int = Field(default=0, description="Total tokens used for LLM")
    error: Optional[str] = Field(None, description="Error message if any")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
