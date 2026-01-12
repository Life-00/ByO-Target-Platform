# app/agents/extractor/state.py
from __future__ import annotations
from typing import TypedDict, List, Optional, Tuple, Dict, Any

from app.schemas.paper import Paper
from app.schemas.fact import Fact


class ExtractorState(TypedDict, total=False):
    papers: List[Paper]

    # (pmid, sentence_id, sentence_text) 큐
    sentence_queue: List[Tuple[str, str, str]]

    current: Optional[Dict[str, Any]]  # {"pmid":..., "sentence_id":..., "text":...}

    # node outputs
    entities: Any
    experiment: Any
    relation: Any

    extracted_facts: List[Fact]