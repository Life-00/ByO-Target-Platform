# app/agents/retriever/paper_filter.py
from __future__ import annotations

from typing import Dict, List, Tuple
import json

from app.core.llm import llm_client, DEFAULT_LLM_MODEL
from app.agents.retriever.prompts import PAPER_FILTER_SYSTEM
from app.schemas.query import UserQuery
from app.schemas.retrieval import Paper


class PaperFilter:
    def __init__(self, keep_eval_n: int = 80, keep_uncertain: bool = True, keep_remaining: bool = False):
        """
        keep_eval_n: LLM이 실제로 평가할 상위 N편
        keep_uncertain: UNCERTAIN을 KEEP 처리할지
        keep_remaining: 평가하지 않은 나머지 논문을 KEEP(=recall 우선)할지, DROP(=precision 우선)할지
        """
        self.keep_eval_n = keep_eval_n
        self.keep_uncertain = keep_uncertain
        self.keep_remaining = keep_remaining

    def filter(self, uq: UserQuery, papers: List[Paper]) -> Tuple[List[Paper], Dict[str, dict]]:
        if not papers:
            return [], {}

        to_eval = papers[: min(self.keep_eval_n, len(papers))]
        remaining = papers[len(to_eval):]

        keep_pmids: set[str] = set()
        meta: Dict[str, dict] = {}

        for p in to_eval:
            abs_text = " ".join([s.text for s in p.abstract_sentences])
            payload = {
                "user_question": uq.intent,
                "target_hint": uq.target_hint,
                "disease": uq.disease,
                "organ": uq.organ,
                "hypothesis": uq.hypothesis,
                "paper": {"title": p.title, "abstract": abs_text, "year": p.year, "journal": p.journal},
            }

            resp = llm_client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": PAPER_FILTER_SYSTEM},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )

            obj = json.loads(resp.choices[0].message.content)
            meta[p.pmid] = obj

            decision = (obj.get("decision") or "").upper()
            if decision == "KEEP":
                keep_pmids.add(p.pmid)
            elif decision == "UNCERTAIN":
                if self.keep_uncertain:
                    keep_pmids.add(p.pmid)
            # DROP은 무시

        if self.keep_remaining:
            for p in remaining:
                keep_pmids.add(p.pmid)

        kept = [p for p in papers if p.pmid in keep_pmids]
        return kept, meta
