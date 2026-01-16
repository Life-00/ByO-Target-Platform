# app/agents/retriever/query_expander.py
from __future__ import annotations

from typing import List, Dict, Any
import json

from app.schemas.query import UserQuery
from app.agents.retriever.types import ExpandedQuery
from app.core.llm import llm_client, DEFAULT_LLM_MODEL
from app.agents.retriever.prompts import QUERY_EXPAND_SYSTEM


class QueryExpander:
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def expand(self, uq: UserQuery) -> List[ExpandedQuery]:
        if self.use_llm:
            try:
                out = self._llm_expand(uq)
                expanded = out.get("expanded_queries") or []
                if expanded:
                    return expanded
            except Exception:
                pass
        return self._rule_expand(uq)

    def _rule_expand(self, uq: UserQuery) -> List[ExpandedQuery]:
        parts = [p for p in [uq.target_hint, uq.disease, uq.organ] if p]
        base = " AND ".join(parts) if parts else (uq.intent or "")

        expanded: List[ExpandedQuery] = []
        if base:
            expanded.append({"query_id": f"{uq.query_id}::q0", "query": base, "reason": "keyword"})

        if uq.hypothesis and base:
            expanded.append(
                {
                    "query_id": f"{uq.query_id}::q1",
                    "query": f"{base} AND ({uq.hypothesis})",
                    "reason": "keyword",
                }
            )

        if uq.intent and uq.intent != base:
            expanded.append({"query_id": f"{uq.query_id}::q2", "query": uq.intent, "reason": "keyword"})

        # 마지막 안전장치
        if not expanded:
            expanded = [{"query_id": f"{uq.query_id}::q0", "query": uq.query_id, "reason": "other"}]

        return expanded

    def _llm_expand(self, uq: UserQuery) -> Dict[str, Any]:
        payload = {
            "query_id": uq.query_id,
            "target_hint": uq.target_hint,
            "disease": uq.disease,
            "organ": uq.organ,
            "intent": uq.intent,
            "hypothesis": uq.hypothesis,
            "constraints": uq.constraints.model_dump() if getattr(uq, "constraints", None) else None,
        }

        resp = llm_client.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": QUERY_EXPAND_SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return json.loads(resp.choices[0].message.content)
