from __future__ import annotations

from typing import List, Optional

from app.agents.retriever.adapters.base import LiteratureAdapter
from app.agents.retriever.pubmed_fetcher import PubMedFetcher
from app.agents.retriever.types import ExpandedQuery
from app.schemas.retrieval import Paper


class PubMedAdapter(LiteratureAdapter):
    source = "pubmed"

    def __init__(self, default_retmax: int = 50):
        self.fetcher = PubMedFetcher(default_retmax=default_retmax)

    def fetch(self, expanded_queries: List[ExpandedQuery], retmax: Optional[int] = None) -> List[Paper]:
        _, pmid_prov = self.fetcher.collect_pmids(expanded_queries, retmax=retmax)
        return PubMedFetcher.fetch_and_parse(expanded_queries, pmid_prov)
