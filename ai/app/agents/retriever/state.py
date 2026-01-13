# app/agents/retriever/state.py
from __future__ import annotations

from typing import Optional, TypedDict

from app.schemas.query import UserQuery
from app.schemas.retrieval import PaperCorpus


class RetrieverState(TypedDict, total=False):
    user_query: UserQuery
    paper_corpus: PaperCorpus
    error: Optional[str]
