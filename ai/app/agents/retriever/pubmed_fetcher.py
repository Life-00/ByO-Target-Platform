# app/agents/retriever/pubmed_fetcher.py
from __future__ import annotations

from typing import Dict, List, Tuple

from app.agents.retriever.types import ExpandedQuery
from app.services.pubmed.client import search_pmids, fetch_medline
from app.services.pubmed.parser import parse_medline
from app.schemas.retrieval import Paper


class PubMedFetcher:
    def __init__(self, default_retmax: int = 50):
        self.default_retmax = default_retmax

    def collect_pmids(self, expanded_queries: List[ExpandedQuery], retmax: int | None = None) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Returns:
          - pmids_by_query: query_id -> [pmid...]
          - pmid_provenance: pmid -> [query_id...]
        """
        pmids_by_query: Dict[str, List[str]] = {}
        pmid_provenance: Dict[str, List[str]] = {}

        n = retmax or self.default_retmax

        for q in expanded_queries:
            qid = q["query_id"]
            term = q["query"]

            pmids = search_pmids(term, retmax=n)
            pmids_by_query[qid] = pmids

            for pmid in pmids:
                pmid_provenance.setdefault(pmid, []).append(qid)

        return pmids_by_query, pmid_provenance

    def fetch_and_parse(self, expanded_queries: List[ExpandedQuery], pmid_provenance: Dict[str, List[str]]) -> List[Paper]:
        """
        Dedup된 PMID들을 fetch하고 Paper로 파싱.
        Paper.query_id는 provenance 중 대표 query_id(첫번째)로 설정.
        """
        qmap = {q["query_id"]: q for q in expanded_queries}

        papers: List[Paper] = []
        for pmid, qids in pmid_provenance.items():
            rep_qid = qids[0]
            reason = qmap.get(rep_qid, {}).get("reason", "keyword")

            record = fetch_medline(pmid)
            paper = parse_medline(
                pmid=pmid,
                record=record,
                query_id=rep_qid,
                retrieval_reason=reason,  # type: ignore
            )
            papers.append(paper)

        return papers
