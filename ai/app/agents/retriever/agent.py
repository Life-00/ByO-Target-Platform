# app/agents/retriever/agent.py
from __future__ import annotations

from app.schemas.query import UserQuery
from app.schemas.retrieval import PaperCorpus
from app.agents.retriever.tool_router import RetrieverToolRouter

class RetrieverAgent:
    def __init__(self, **kwargs):
        self.router = RetrieverToolRouter(**kwargs)

    def run(self, user_query: UserQuery) -> PaperCorpus:
        return self.router.run(user_query)