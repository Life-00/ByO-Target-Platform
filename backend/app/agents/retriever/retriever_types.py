# app/agents/retriever/types.py
from __future__ import annotations
from typing import TypedDict, Literal, List, Dict, Optional


RetrievalReasonStr = Literal["keyword", "synonym", "mesh", "other"]


class ExpandedQuery(TypedDict):
    query_id: str
    query: str
    reason: RetrievalReasonStr


class FilterDecision(TypedDict):
    decision: Literal["KEEP", "DROP", "UNCERTAIN"]
    confidence: float
    reasons: List[str]
    checklist: Dict[str, Dict[str, str]]