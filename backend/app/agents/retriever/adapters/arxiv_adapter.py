from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Optional

import httpx

from app.agents.retriever.adapters.base import LiteratureAdapter
from app.agents.retriever.types import ExpandedQuery
from app.schemas.retrieval import AbstractSentence, Paper
from app.service.pubmed.parser import split_sentences

ARXIV_URL = "https://export.arxiv.org/api/query"


class ArxivAdapter(LiteratureAdapter):
    source = "arxiv"

    def __init__(self, default_retmax: int = 50):
        self.default_retmax = default_retmax

    def fetch(self, expanded_queries: List[ExpandedQuery], retmax: Optional[int] = None) -> List[Paper]:
        limit = retmax or self.default_retmax
        papers: List[Paper] = []
        for q in expanded_queries:
            resp = httpx.get(
                ARXIV_URL,
                params={"search_query": f"all:{q['query']}", "max_results": str(limit)},
                timeout=10.0,
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("a:entry", ns):
                papers.append(self._to_paper(entry, ns, q["query_id"], q["reason"]))
        return papers

    def _to_paper(self, entry: ET.Element, ns: dict, query_id: str, reason: str) -> Paper:
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        arxiv_id = (entry.findtext("a:id", default="", namespaces=ns) or "").split("/")[-1]
        pdf_url = None
        url = None
        for link in entry.findall("a:link", ns):
            rel = link.get("rel")
            if rel == "alternate":
                url = link.get("href")
            if link.get("title") == "pdf":
                pdf_url = link.get("href")
        summary = entry.findtext("a:summary", default="", namespaces=ns) or ""
        sentences = [
            AbstractSentence(sentence_id=f"{arxiv_id}_s{i}", text=s)
            for i, s in enumerate(split_sentences(summary))
        ]
        authors = [
            a.findtext("a:name", default="", namespaces=ns)
            for a in entry.findall("a:author", ns)
            if a.findtext("a:name", default="", namespaces=ns)
        ]
        year = None
        published = entry.findtext("a:published", default="", namespaces=ns) or ""
        if published:
            year = int(published[:4])
        return Paper(
            source="arxiv",
            source_id=arxiv_id,
            pmid=None,
            doi=None,
            url=url,
            pdf_url=pdf_url,
            license=None,
            has_fulltext=bool(url or pdf_url),
            title=title,
            journal="arXiv",
            year=year,
            authors=authors,
            abstract_sentences=sentences,
            retrieval_reason=reason,
            query_id=query_id,
        )
