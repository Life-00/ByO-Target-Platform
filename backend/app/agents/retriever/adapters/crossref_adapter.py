from __future__ import annotations

from typing import List, Optional

import httpx

from app.agents.retriever.adapters.base import LiteratureAdapter
from app.agents.retriever.types import ExpandedQuery
from app.schemas.retrieval import AbstractSentence, Paper
from app.service.pubmed.parser import split_sentences

BASE_URL = "https://api.crossref.org/works"


class CrossrefAdapter(LiteratureAdapter):
    source = "crossref"

    def __init__(self, default_retmax: int = 50, oa_only: bool = True):
        self.default_retmax = default_retmax
        self.oa_only = oa_only

    def fetch(self, expanded_queries: List[ExpandedQuery], retmax: Optional[int] = None) -> List[Paper]:
        limit = retmax or self.default_retmax
        papers: List[Paper] = []
        for q in expanded_queries:
            params = {"query": q["query"], "rows": str(limit)}
            if self.oa_only:
                params["filter"] = "license.url:*"
            resp = httpx.get(BASE_URL, params=params, timeout=10.0)
            resp.raise_for_status()
            items = resp.json().get("message", {}).get("items", []) or []
            for item in items:
                papers.append(self._to_paper(item, q["query_id"], q["reason"]))
        return papers

    def _to_paper(self, item: dict, query_id: str, reason: str) -> Paper:
        doi = item.get("DOI")
        pdf_url = next(
            (l.get("URL") for l in item.get("link", []) if l.get("content-type") == "application/pdf"),
            None,
        )
        url = pdf_url or item.get("URL")
        license_url = (item.get("license") or [{}])[0].get("URL")
        abstract = item.get("abstract") or ""
        sentences = [
            AbstractSentence(sentence_id=f"{doi or item.get('URL','unknown')}_s{i}", text=s)
            for i, s in enumerate(split_sentences(abstract))
        ]
        year = None
        if item.get("issued", {}).get("date-parts"):
            year = item["issued"]["date-parts"][0][0]
        authors = []
        for a in item.get("author", []):
            name = " ".join(filter(None, [a.get("given"), a.get("family")]))
            if name:
                authors.append(name)
        return Paper(
            source="crossref",
            source_id=doi or item.get("URL", ""),
            pmid=None,
            doi=doi,
            url=url,
            pdf_url=pdf_url,
            license=license_url,
            has_fulltext=bool(url or pdf_url),
            title=" ".join(item.get("title", [])),
            journal=(item.get("container-title") or [None])[0],
            year=year,
            authors=authors,
            abstract_sentences=sentences,
            retrieval_reason=reason,
            query_id=query_id,
        )
