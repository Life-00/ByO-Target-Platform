# app/agents/retriever/europe_pmc_fetcher.py
from __future__ import annotations
import requests
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import time
from app.schemas.retrieval import Paper, AbstractSentence

@dataclass
class EuropePMCResult:
    source: str
    id: str
    title: str
    abstract: str
    year: Optional[int]
    journal: Optional[str]
    authors: List[str]
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None

class EuropePMCFetcher:
    def __init__(self, timeout: float = 20.0):
        self.base = "https://www.ebi.ac.uk/europepmc/webservices/rest"
        self.timeout = timeout

    def search(self, query: str, page_size: int = 10, sort: str = "relevance") -> List[EuropePMCResult]:
        url = f"{self.base}/search"
        params = {
            "query": query,
            "format": "json",
            "pageSize": page_size,
            "resultType": "core",
            "sort": sort,
        }
        resp = requests.get(url, params=params, timeout=self.timeout)
        print("[EPMC] status:", resp.status_code)
        if resp.status_code != 200:
            print("[EPMC] body:", resp.text[:500])
            return []
        data = resp.json() or {}
        print("[EPMC] hitCount:", data.get("hitCount"))

        items = (data.get("resultList") or {}).get("result") or []
        print("[EPMC] parsed_results:", len(items))

        out = []
        for it in items:
            author_str = (it.get("authorString") or "").strip()
            authors = [a.strip() for a in author_str.split(",") if a.strip()] if author_str else []
            y = (it.get("pubYear") or "").strip()
            year = int(y) if y.isdigit() else None

            source = (it.get("source") or "").strip()
            rid = (it.get("id") or "").strip()
            url2 = f"https://europepmc.org/article/{source}/{rid}" if (source and rid) else None

            out.append(EuropePMCResult(
                source=source,
                id=rid,
                title=(it.get("title") or "").strip(),
                abstract=(it.get("abstractText") or "").strip(),
                year=year,
                journal=(it.get("journalTitle") or it.get("journal") or "").strip() or None,
                authors=authors,
                pmid=(it.get("pmid") or "").strip() or None,
                pmcid=(it.get("pmcid") or "").strip() or None,
                doi=(it.get("doi") or "").strip() or None,
                url=url2,
            ))
        return out



    @staticmethod
    def to_paper(r: EuropePMCResult, query_id: str, retrieval_reason: str = "europe_pmc_search") -> Paper:
        sentences = [s.strip() for s in (r.abstract or "").split(".") if len(s.strip()) > 10]
        abs_sentences = [AbstractSentence(sentence_id=f"{r.source}_{r.id}_{i}", text=s) for i, s in enumerate(sentences)]

        # Paper.pmid는 필수라서:
        # - PubMed 논문이면 PMID를 우선
        # - 아니면 source:id 형태로 내부 식별자 부여
        internal_id = r.pmid or r.pmcid or f"{r.source}:{r.id}"
        src = (r.source or "").lower()
        if "biorxiv" in (r.journal or "").lower():
            src = "biorxiv"
            
        return Paper(
            pmid=str(internal_id),
            title=r.title or "(no title)",
            year=r.year,
            journal=r.journal,
            authors=r.authors,
            abstract_sentences=abs_sentences,
            retrieval_reason=retrieval_reason,
            query_id=query_id,
            url=r.url,
            source=src or "europe_pmc",
            # pdf_storage_path는 다운로드 단계에서 채움
        )
