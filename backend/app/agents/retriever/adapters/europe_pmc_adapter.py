from __future__ import annotations

from typing import List, Optional

import httpx

from app.agents.retriever.adapters.base import LiteratureAdapter
from app.agents.retriever.types import ExpandedQuery
from app.schemas.retrieval import AbstractSentence, Paper
from app.service.pubmed.parser import split_sentences

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class EuropePmcAdapter(LiteratureAdapter):
    source = "europe_pmc"

    def __init__(self, page_size: int = 50, oa_only: bool = True):
        self.page_size = page_size
        self.oa_only = oa_only

    def fetch(self, expanded_queries: List[ExpandedQuery], retmax: Optional[int] = None) -> List[Paper]:
        limit = retmax or self.page_size
        papers: List[Paper] = []
        for q in expanded_queries:
            query = f"{q['query']} AND OPEN_ACCESS:Y" if self.oa_only else q["query"]
            resp = httpx.get(
                BASE_URL,
                params={"query": query, "format": "json", "pageSize": str(limit)},
                timeout=10.0,
            )
            resp.raise_for_status()
            results = resp.json().get("resultList", {}).get("result", []) or []
            for rec in results:
                if self.oa_only and rec.get("isOpenAccess") != "Y":
                    continue
                papers.append(self._to_paper(rec, q["query_id"], q["reason"]))
        return papers

    def _to_paper(self, rec: dict, query_id: str, reason: str) -> Paper:
        pmid = rec.get("pmid") or rec.get("id")
        doi = rec.get("doi")
        urls = rec.get("fullTextUrlList", {}).get("fullTextUrl", []) or []
        pdf_url = next((u.get("url") for u in urls if u.get("documentStyle") == "pdf"), None)
        fulltext_url = pdf_url or (urls[0].get("url") if urls else None)
        abstract_text = rec.get("abstractText", "") or ""
        sentences = [
            AbstractSentence(sentence_id=f"{pmid or rec.get('id')}_s{i}", text=s)
            for i, s in enumerate(split_sentences(abstract_text))
        ]
        year = int(rec["pubYear"]) if str(rec.get("pubYear", "")).isdigit() else None
        authors = [
            a.get("fullName")
            for a in rec.get("authorList", {}).get("author", [])
            if a.get("fullName")
        ]
        return Paper(
            source="europe_pmc",
            source_id=rec.get("id", pmid or doi or ""),
            pmid=pmid,
            doi=doi,
            url=fulltext_url or rec.get("url"),
            pdf_url=pdf_url,
            license=rec.get("license"),
            has_fulltext=bool(fulltext_url or pdf_url),
            title=rec.get("title", ""),
            journal=rec.get("journalTitle") or None,
            year=year,
            authors=authors,
            abstract_sentences=sentences,
            retrieval_reason=reason,
            query_id=query_id,
        )
