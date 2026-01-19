from __future__ import annotations

from typing import List, Optional

from app.agents.retriever.types import ExpandedQuery
from app.schemas.retrieval import Paper


class MultiSourceFetcher:
    def __init__(self, adapters: List):
        self.adapters = adapters

    def fetch(self, expanded_queries: List[ExpandedQuery], retmax: Optional[int] = None) -> List[Paper]:
        collected: List[Paper] = []
        for adapter in self.adapters:
            collected.extend(adapter.fetch(expanded_queries, retmax=retmax))
        return self._dedupe(collected)

    def _dedupe(self, papers: List[Paper]) -> List[Paper]:
        seen = set()
        deduped: List[Paper] = []
        for p in papers:
            key = p.doi or p.pmid or p.url or p.title.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(p)
        return deduped
