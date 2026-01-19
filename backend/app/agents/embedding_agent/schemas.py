"""
EmbeddingAgent Input/Output Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class EmbeddingAgentInputSchema(BaseModel):
    """Input schema for embedding agent"""
    document_id: int = Field(..., description="Document ID to process")
    session_id: Optional[str] = Field(None, description="Session ID")
    chunk_size: int = Field(3200, description="Maximum tokens per chunk (Upstage limit: 4096)", ge=500, le=4000)


class EmbeddingAgentOutputSchema(BaseModel):
    """Output schema for embedding agent"""
    success: bool = Field(..., description="Whether processing was successful")
    document_id: int = Field(..., description="Processed document ID")
    chunk_count: int = Field(0, description="Number of chunks created")
    embedding_count: int = Field(0, description="Number of embeddings generated")
    status: str = Field("pending", description="Processing status")
    error: Optional[str] = Field(None, description="Error message if any")
    data: dict = Field(default_factory=dict, description="Additional data")
