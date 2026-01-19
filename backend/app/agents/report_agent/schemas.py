"""
Report Agent Schemas
Input and output data models for research feasibility report generation
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DocumentReference(BaseModel):
    """Reference to a document used in analysis"""
    id: Optional[int] = Field(None, description="Document ID")
    title: str = Field(..., description="Document title")
    authors: Optional[str] = Field(None, description="Document authors")
    year: Optional[int] = Field(None, description="Publication year")


class ResearchTopicData(BaseModel):
    """Research topic and related documents"""
    topic: Optional[str] = Field(None, description="Research topic/hypothesis")
    description: Optional[str] = Field(None, description="Detailed description")
    analysis_goal: Optional[str] = Field(None, description="Analysis focus")
    related_documents: List[DocumentReference] = Field(
        default_factory=list,
        description="Documents relevant to the topic"
    )
    
    class Config:
        extra = "allow"  # Allow extra fields


class ReportAgentRequest(BaseModel):
    """Input schema for report generation"""
    research_topic: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Research topic/hypothesis to validate"
    )
    research_data: Optional[ResearchTopicData] = Field(
        None,
        description="Research data including topic and related documents"
    )
    report_type: str = Field(
        default="comprehensive",
        description="Report type: comprehensive, summary, or detailed"
    )
    include_visualizations: bool = Field(
        default=False,
        description="Include graphs and visualizations in report"
    )
    include_network_graph: bool = Field(
        default=False,
        description="Include research evidence network graph"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for creative analysis"
    )
    max_tokens: int = Field(
        default=2048,
        ge=1000,
        le=8192,
        description="Maximum tokens in response"
    )
    
    class Config:
        extra = "allow"  # Allow extra fields


class ResearchValidation(BaseModel):
    """Research feasibility validation result"""
    is_feasible: bool = Field(..., description="Is research feasible?")
    feasibility_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Feasibility score (0-100)"
    )
    reasoning: str = Field(..., description="Explanation of feasibility assessment")


class ReportSection(BaseModel):
    """A section within the report"""
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    citations: List[str] = Field(
        default_factory=list,
        description="References to documents"
    )


class ResearchReport(BaseModel):
    """Comprehensive research feasibility report"""
    title: str = Field(..., description="Report title")
    research_topic: str = Field(..., description="Original research topic")
    validation: ResearchValidation = Field(
        ...,
        description="Feasibility validation results"
    )
    sections: List[ReportSection] = Field(
        ...,
        description="Report sections"
    )
    evidence_summary: str = Field(
        ...,
        description="Summary of evidence from literature"
    )
    recommendations: List[str] = Field(
        ...,
        description="Recommendations for research"
    )
    limitations: List[str] = Field(
        ...,
        description="Limitations and considerations"
    )
    related_papers: List[DocumentReference] = Field(
        default_factory=list,
        description="Papers referenced in report"
    )


class ReportAgentResponse(BaseModel):
    """Output schema for report generation"""
    report: ResearchReport = Field(..., description="Generated research report")
    visualizations: Dict[str, str] = Field(
        default_factory=dict,
        description="Visualization HTML strings"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    tokens_used: int = Field(default=0, description="Tokens consumed")
    report_format: str = Field(
        default="json",
        description="Format: json, markdown, or docx"
    )
