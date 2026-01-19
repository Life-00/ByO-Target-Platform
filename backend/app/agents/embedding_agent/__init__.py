"""
EmbeddingAgent package
"""

from app.agents.embedding_agent.agent import EmbeddingAgent
from app.agents.embedding_agent.schemas import (
    EmbeddingAgentInputSchema,
    EmbeddingAgentOutputSchema,
)

__all__ = [
    "EmbeddingAgent",
    "EmbeddingAgentInputSchema",
    "EmbeddingAgentOutputSchema",
]
