# app/agents/retriever/pubmed_fetcher.py
from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from app.agents.retriever.retriever_types import ExpandedQuery
from app.service.pubmed import client as pubmed_client
from app.service.pubmed.parser import parse_medline
from app.schemas.retrieval import Paper

class PubMedFetcher:
    def __init__(self, default_retmax: int = 50):
        self.default_retmax = default_retmax

    def collect_pmids(
        self,
        expanded_queries: List[ExpandedQuery],
        retmax: Optional[int] = None,
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        [PMC 우선 모드] 
        1. db=pmc를 사용하여 전문 확보가 가능한 논문 위주로 PMID를 수집합니다.
        2. 검색어에 'free fulltext' 필터를 자동으로 적용합니다.
        """
        n = retmax or self.default_retmax
        pmids_by_query: Dict[str, List[str]] = {}
        pmid_provenance: Dict[str, List[str]] = {}

        for q in expanded_queries:
            qid = q["query_id"]
            # PMC 전문 확보 확률을 높이기 위해 필터 추가
            term = f"{q['query']} AND \"free full text\"[Filter]"
            
            print(f"[PMC-Fetch] PMC 데이터베이스에서 검색 중: {term}")
            
            # PMC 전용 엔드포인트 호출 (db='pmc' 파라미터 전달)
            # pubmed_client.search_pmids 내부에서 db=pmc를 처리하도록 구성됨
            pmids = pubmed_client.search_pmids(term, n, db="pmc")
            
            print(f"[PMC-Fetch] 쿼리 ID {qid}: {len(pmids)}개의 PMCID 발견")
            pmids_by_query[qid] = pmids

            for pmid in pmids:
                # PMC ID는 종종 PMID와 혼용되거나 변환이 필요하므로 출처 관리
                pmid_provenance.setdefault(pmid, []).append(qid)

        return pmids_by_query, pmid_provenance

    @staticmethod
    def fetch_and_parse(
        expanded_queries: List[ExpandedQuery],
        pmid_provenance: Dict[str, List[str]],
    ) -> List[Paper]:
        """PMC 데이터를 기반으로 상세 정보를 파싱합니다."""
        qmap = {q["query_id"]: q for q in expanded_queries}
        papers: List[Paper] = []

        for pmid, qids in pmid_provenance.items():
            rep_qid = qids[0]
            reason = qmap.get(rep_qid, {}).get("reason", "keyword")

            print(f"[PMC-Fetch] 상세 정보 로드 중 (ID: {pmid})...")
            # db='pmc'를 사용하여 전문 메타데이터 로드
            record = pubmed_client.fetch_medline(pmid, db="pmc")
            
            if not record:
                print(f"[PMC-Fetch] ID {pmid} 데이터 로드 실패. 건너뜁니다.")
                continue

            paper = parse_medline(
                pmid=pmid,
                record=record,
                query_id=rep_qid,
                retrieval_reason=reason,
            )
            papers.append(paper)

        return papers