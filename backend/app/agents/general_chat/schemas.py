"""
General Chat Agent Schemas
Input and output data models for general chat agent
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """General chat request schema"""
    content: str = Field(..., description="User message content")
    system_prompt: Optional[str] = Field(None, description="System prompt override")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature")
    max_tokens: int = Field(default=2048, ge=100, le=4096, description="Max tokens")
    selected_documents: Optional[List[Dict[str, Any]]] = Field(None, description="Selected documents for context")
    analysis_goal: Optional[str] = Field(None, description="Analysis goal")


class ChatResponse(BaseModel):
    """General chat response schema"""
    content: str = Field(..., description="LLM response content")
    tokens_used: int = Field(default=0, description="Tokens used")
    model: str = Field(default="solar-1-mini-chat", description="Model used")
