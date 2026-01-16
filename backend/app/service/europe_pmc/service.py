from __future__ import annotations

from typing import Dict, List, Tuple

from app.services.europe_pmc.client import EuropePMCClient
from app.services.europe_pmc.parser import parse_epmc_result
from app.schemas.retrieval import Paper


epmc_client = EuropePMCClient()


def search_epmc_as_papers(
    queries: List[Tuple[str, str, str]],  # (query_id, query_string, reason)
    retmax_per_query: int = 50,
) -> Tuple[Dict[str, List[str]], Dict[str, List[dict]], List[Paper]]:
    """
    Retriever-friendly:
    - pmids_by_query: query_id -> [paper_id...]
    - raw_by_paper_id: paper_id -> raw result dict (later enrichment용)
    - papers: Paper[]
    """
    pmids_by_query: Dict[str, List[str]] = {}
    raw_by_paper_id: Dict[str, List[dict]] = {}
    papers: List[Paper] = []

    for qid, qstr, reason in queries:
        # pageSize는 retmax를 그대로 사용 (cursor paging까지 완벽히 하려면 반복)
        data = epmc_client.search(query=qstr, page_size=retmax_per_query, result_type="core")

        results = data.get("resultList", {}).get("result", []) or []
        ids: List[str] = []

        for r in results:
            p = parse_epmc_result(r, query_id=qid, retrieval_reason=reason)
            if not p:
                continue
            ids.append(p.pmid)
            raw_by_paper_id.setdefault(p.pmid, []).append(r)
            papers.append(p)

        # de-dup(순서 유지)
        seen = set()
        pmids_by_query[qid] = [x for x in ids if not (x in seen or seen.add(x))]

    return pmids_by_query, raw_by_paper_id, papers
