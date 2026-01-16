# app/agents/retriever/pubmed_fetcher.py
from __future__ import annotations

from typing import Dict, List, Tuple, Optional, Any

from app.agents.retriever.types import ExpandedQuery
from app.service.pubmed import client as pubmed_client
from app.service.pubmed.parser import parse_medline
from app.schemas.retrieval import Paper


class PubMedFetcher:
    """
    PMC(Full-text/PDF 가능성 높은 소스) 중심 검색/메타데이터 로드 Fetcher

    - collect_pmids(): 확장 검색어(ExpandedQuery)들을 기반으로 PMID 목록을 수집
    - fetch_and_parse(): PMID들을 fetch_medline로 가져와 Paper로 파싱
    """

    def __init__(self, default_retmax: int = 50):
        self.default_retmax = default_retmax

    # ---------------------------
    # Compatibility wrappers
    # ---------------------------
    def _search_pmids_compat(self, term: str, n: int, db: str):
        """
        pubmed_client.search_pmids 시그니처가 환경마다 달라서
        - db 키워드 지원
        - db 포지셔널 지원
        - db 미지원
        를 모두 커버한다.
        """
        try:
            return pubmed_client.search_pmids(term, n, db=db)
        except TypeError:
            try:
                return pubmed_client.search_pmids(term, n, db)
            except TypeError:
                return pubmed_client.search_pmids(term, n)

    def _fetch_medline_compat(self, pmid: str, db: str):
        """
        pubmed_client.fetch_medline도 동일하게 db 호환 처리
        """
        try:
            return pubmed_client.fetch_medline(pmid, db=db)
        except TypeError:
            try:
                return pubmed_client.fetch_medline(pmid, db)
            except TypeError:
                return pubmed_client.fetch_medline(pmid)

    # ---------------------------
    # Utilities for ExpandedQuery
    # ---------------------------
    def _get_attr(self, obj: Any, *names: str, default=None):
        for n in names:
            if isinstance(obj, dict) and n in obj:
                v = obj.get(n)
                if v is not None:
                    return v
            if hasattr(obj, n):
                v = getattr(obj, n)
                if v is not None:
                    return v
        return default

    def _extract_query_id(self, q: ExpandedQuery) -> str:
        qid = self._get_attr(q, "query_id", "id", "qid", default=None)
        if not qid:
            # 마지막 fallback: term 기반으로 임시 id
            term = self._extract_term(q)
            return f"q_{abs(hash(term))}"
        return str(qid)

    def _extract_term(self, q: ExpandedQuery) -> str:
        # ExpandedQuery 구현이 프로젝트마다 달라서 폭넓게 커버
        term = self._get_attr(
            q,
            "term",
            "query",
            "query_text",
            "expanded_query",
            "expanded_term",
            "text",
            default="",
        )
        return str(term or "").strip()

    def _extract_reason(self, q: ExpandedQuery) -> str:
        reason = self._get_attr(q, "reason", "strategy", "source", default=None)
        return str(reason) if reason else "keyword"

    # ---------------------------
    # Public APIs
    # ---------------------------
    def collect_pmids(
        self,
        expanded_queries: List[ExpandedQuery],
        retmax: Optional[int] = None,
        db: str = "pmc",
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Returns:
          - pmids_by_query: query_id -> pmids
          - pmid_provenance: pmid -> [query_id, ...]
        """
        n = retmax or self.default_retmax

        pmids_by_query: Dict[str, List[str]] = {}
        pmid_provenance: Dict[str, List[str]] = {}

        for q in expanded_queries:
            qid = self._extract_query_id(q)
            term = self._extract_term(q)
            if not term:
                continue

            try:
                pmids = self._search_pmids_compat(term, n, db=db) or []
            except Exception as e:
                print(f"[PMC-Fetch] search_pmids 실패 (qid={qid}) term='{term}': {e}")
                pmids = []

            # normalize list[str]
            pmids = [str(p).strip() for p in pmids if str(p).strip()]
            # de-dup but keep order
            seen = set()
            pmids = [p for p in pmids if not (p in seen or seen.add(p))]

            pmids_by_query[qid] = pmids

            for pmid in pmids:
                pmid_provenance.setdefault(pmid, []).append(qid)

        return pmids_by_query, pmid_provenance

    def fetch_and_parse(
        self,
        expanded_queries: List[ExpandedQuery],
        pmid_provenance: Dict[str, List[str]],
        db: str = "pmc",
    ) -> List[Paper]:
        """
        pmid_provenance를 기반으로 대표 query_id/이유를 붙여 Paper로 파싱
        """
        # qid -> reason 맵 구성
        qmap: Dict[str, Dict[str, str]] = {}
        for q in expanded_queries:
            qid = self._extract_query_id(q)
            qmap[qid] = {"reason": self._extract_reason(q)}

        papers: List[Paper] = []

        # 안정적 순서
        for pmid in sorted(pmid_provenance.keys()):
            qids = pmid_provenance.get(pmid) or []
            rep_qid = qids[0] if qids else "keyword"
            reason = qmap.get(rep_qid, {}).get("reason", "keyword")

            try:
                record = self._fetch_medline_compat(pmid, db=db)
            except Exception as e:
                print(f"[PMC-Fetch] fetch_medline 실패 pmid={pmid}: {e}")
                continue

            if not record:
                print(f"[PMC-Fetch] ID {pmid} 데이터 로드 실패. 건너뜁니다.")
                continue

            try:
                paper = parse_medline(
                    pmid=pmid,
                    record=record,
                    query_id=rep_qid,
                    retrieval_reason=reason,  # type: ignore
                )
                papers.append(paper)
            except Exception as e:
                print(f"[PMC-Fetch] parse_medline 실패 pmid={pmid}: {e}")
                continue

        return papers
