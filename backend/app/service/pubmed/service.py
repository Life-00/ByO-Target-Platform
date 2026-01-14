# app/services/pubmed/service.py
from __future__ import annotations

from typing import Dict, List, Tuple, Optional

from app.schemas.query import UserQuery
from app.schemas.retrieval import Paper, PaperCorpus, RetrievalReason

from app.service.pubmed.client import search_pmids, fetch_medline
from app.service.pubmed.parser import parse_medline


def build_query_string(uq: UserQuery) -> str:
    """
    단일 쿼리 구성(보수적).
    - RetrieverAgent에서 쿼리 확장을 별도로 한다면, 이 함수는 'fallback/legacy' 용도로만 사용.
    """
    terms = []
    if uq.target_hint:
        terms.append(uq.target_hint)
    if uq.disease:
        terms.append(uq.disease)
    if uq.organ:
        terms.append(uq.organ)
    if not terms and uq.intent:
        terms.append(uq.intent)
    return " AND ".join(terms)


# ✅ Retriever가 사용하기 좋은 "배치 조합 함수"
def collect_pmids_for_queries(
    queries: List[Tuple[str, str]],
    retmax: int,
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    여러 쿼리를 돌려 PMID를 모으고 provenance를 만든다.

    Args:
      queries: [(query_id, query_string), ...]
      retmax: query당 최대 PMID 수

    Returns:
      pmids_by_query: query_id -> [pmid...]
      pmid_provenance: pmid -> [query_id...]
    """
    pmids_by_query: Dict[str, List[str]] = {}
    pmid_provenance: Dict[str, List[str]] = {}

    for qid, qstr in queries:
        pmids = search_pmids(qstr, retmax)
        pmids_by_query[qid] = pmids
        for pmid in pmids:
            pmid_provenance.setdefault(pmid, []).append(qid)

    return pmids_by_query, pmid_provenance


def fetch_and_parse_papers(
    pmid_provenance: Dict[str, List[str]],
    query_reason_by_qid: Optional[Dict[str, RetrievalReason]] = None,
) -> List[Paper]:
    """
    Dedup된 PMID들을 fetch+parse 해서 Paper 리스트로 반환한다.
    - Paper.query_id는 provenance의 첫 query_id(rep)로 설정
    - retrieval_reason은 query_reason_by_qid에서 찾아 주입(없으면 keyword)
    """
    query_reason_by_qid = query_reason_by_qid or {}

    papers: List[Paper] = []
    for pmid, qids in pmid_provenance.items():
        rep_qid = qids[0]
        reason = query_reason_by_qid.get(rep_qid, "keyword")

        medline = fetch_medline(pmid)
        paper = parse_medline(
            pmid=pmid,
            record=medline,
            query_id=rep_qid,
            retrieval_reason=reason,
        )
        papers.append(paper)

    return papers

def search_pubmed(uq: UserQuery) -> PaperCorpus:
    """
    Legacy 단일 검색. 전략 없음.
    """
    query = build_query_string(uq)
    retmax = uq.constraints.max_results if (uq.constraints and uq.constraints.max_results) else 5
    pmids = search_pmids(query, retmax)

    papers: List[Paper] = []
    for pmid in pmids:
        medline = fetch_medline(pmid)
        paper = parse_medline(
            pmid=pmid,
            record=medline,
            query_id=uq.query_id,
            retrieval_reason="keyword",
        )
        papers.append(paper)

    return PaperCorpus(query_id=uq.query_id, papers=papers)
