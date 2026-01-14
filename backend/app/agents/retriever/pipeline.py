# app/agents/retriever/pipeline.py
from __future__ import annotations

from app.schemas.query import UserQuery
from app.schemas.retrieval import PaperCorpus

from app.agents.retriever.query_expander import QueryExpander
from app.agents.retriever.pubmed_fetcher import PubMedFetcher
from app.agents.retriever.semantic_ranker import SemanticRanker
from app.agents.retriever.paper_filter import PaperFilter


class RetrieverPipeline:
    def __init__(
            self,
            use_llm_expand: bool = True,
            use_llm_filter: bool = True,
            default_retmax: int = 300,
            semantic_top_n: int = 200,
            llm_keep_eval_n: int = 80,
            use_knee_cutoff: bool = True,
            knee_min_k: int = 5,
            knee_max_k: int | None = None,
    ):
        self.expander = QueryExpander(use_llm=use_llm_expand)
        self.fetcher = PubMedFetcher(default_retmax=default_retmax)
        self.ranker = SemanticRanker(
            use_knee_cutoff=use_knee_cutoff,
            knee_min_k=knee_min_k,
            knee_max_k=knee_max_k or semantic_top_n,  # cap by top_n if not provided
        )
        self.filter = PaperFilter(keep_eval_n=llm_keep_eval_n)

        self.use_llm_filter = use_llm_filter
        self.semantic_top_n = semantic_top_n

    def run(self, uq: UserQuery) -> PaperCorpus:
        print(f"[Pipeline] 1. Query Expansion 시작... (ID: {uq.query_id})") # ✅ 로그 추가
        
        # 1) Query expansion
        expanded_queries = self.expander.expand(uq)
        print(f"[Pipeline]    - 확장된 검색어 개수: {len(expanded_queries)}") # ✅ 로그 추가

        # 2) Collect PMIDs
        retmax = None
        if getattr(uq, "constraints", None) is not None:
            retmax = getattr(uq.constraints, "max_results", None)

        print(f"[Pipeline] 2. PubMed ID 수집 중... (Max: {retmax or self.fetcher.default_retmax})") # ✅ 로그 추가
        _, pmid_prov = self.fetcher.collect_pmids(expanded_queries, retmax=retmax)
        print(f"[Pipeline]    - 수집된 PMID 개수: {len(pmid_prov)}") # ✅ 로그 추가

        # 3) Fetch + parse
        print(f"[Pipeline] 3. 논문 상세 정보(Abstract) 다운로드 중...") # ✅ 로그 추가
        papers_raw = PubMedFetcher.fetch_and_parse(expanded_queries, pmid_prov)
        print(f"[Pipeline]    - 다운로드 완료: {len(papers_raw)}건") # ✅ 로그 추가

        # 4) Semantic rerank + topN
        print(f"[Pipeline] 4. 의미 기반 랭킹(Semantic Ranking) 계산 중...") # ✅ 로그 추가
        qtext = " ".join(
            [t for t in [uq.target_hint, uq.disease, uq.organ, uq.intent, uq.hypothesis] if t]
        )
        papers_topn, _scores = self.ranker.rank(qtext, papers_raw, top_n=self.semantic_top_n)
        print(f"[Pipeline]    - 랭킹 상위 {len(papers_topn)}건 선정 완료") # ✅ 로그 추가

        # 5) keep/drop (optional)
        if self.use_llm_filter:
            print(f"[Pipeline] 5. LLM 필터링(Paper Filter) 진행 중... (시간 소요됨)") # ✅ 로그 추가
            kept, _meta = self.filter.filter(uq, papers_topn)
            final_papers = kept
            print(f"[Pipeline]    - 최종 통과 논문: {len(final_papers)}건") # ✅ 로그 추가
        else:
            final_papers = papers_topn
            print(f"[Pipeline] 5. LLM 필터링 건너뜀 (설정: OFF)") # ✅ 로그 추가

        # 6) Output
        print(f"[Pipeline] ✅ 모든 작업 완료!") # ✅ 로그 추가
        return PaperCorpus(query_id=uq.query_id, papers=final_papers)
