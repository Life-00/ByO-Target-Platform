# app/agents/retriever/agent.py
from __future__ import annotations

from app.schemas.query import UserQuery
from app.schemas.retrieval import PaperCorpus
from app.agents.retriever.pipeline import RetrieverPipeline


class RetrieverAgent:
    def __init__(
            self,
            use_llm_expand: bool = True,
            use_llm_filter: bool = True,
            default_retmax: int = 50,
            semantic_top_n: int = 200,
            llm_keep_eval_n: int = 80,
            use_knee_cutoff: bool = True,
            knee_min_k: int = 5,
            knee_max_k: int | None = None,
    ):
        self.pipeline = RetrieverPipeline(
            use_llm_expand=use_llm_expand,
            use_llm_filter=use_llm_filter,
            default_retmax=default_retmax,
            semantic_top_n=semantic_top_n,
            llm_keep_eval_n=llm_keep_eval_n,
            use_knee_cutoff=use_knee_cutoff,
            knee_min_k=knee_min_k,
            knee_max_k=knee_max_k or semantic_top_n,
        )

    def run(self, user_query: UserQuery) -> PaperCorpus:
        return self.pipeline.run(user_query)
