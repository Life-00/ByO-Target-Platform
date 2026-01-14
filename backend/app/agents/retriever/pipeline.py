from __future__ import annotations
import time
import json

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
            knee_max_k=knee_max_k or semantic_top_n,
        )
        self.filter = PaperFilter(keep_eval_n=llm_keep_eval_n)

        self.use_llm_filter = use_llm_filter
        self.semantic_top_n = semantic_top_n

    # ✅ run 대신 run_stream 사용 (Generator)
    def run_stream(self, uq: UserQuery):
        # 1) Query expansion
        yield {"type": "log", "content": f"🔎 검색어 확장 중... (ID: {uq.query_id})"}
        expanded_queries = self.expander.expand(uq)
        yield {"type": "log", "content": f"   👉 확장된 검색어 {len(expanded_queries)}개 생성됨"}

        # 2) Collect PMIDs
        retmax = None
        if getattr(uq, "constraints", None) is not None:
            retmax = getattr(uq.constraints, "max_results", None)

        yield {"type": "log", "content": f"📄 PubMed ID 수집 중... (Max: {retmax or self.fetcher.default_retmax})"}
        _, pmid_prov = self.fetcher.collect_pmids(expanded_queries, retmax=retmax)
        yield {"type": "log", "content": f"   👉 총 {len(pmid_prov)}개의 고유 PMID 수집 완료"}

        if not pmid_prov:
            yield {"type": "log", "content": "⚠️ 수집된 논문이 없습니다. 프로세스 종료."}
            yield {"type": "result", "data": PaperCorpus(query_id=uq.query_id, papers=[])}
            return

        # 3) Fetch + parse
        yield {"type": "log", "content": "📥 논문 초록(Abstract) 다운로드 및 파싱 중..."}
        start_t = time.time()
        papers_raw = PubMedFetcher.fetch_and_parse(expanded_queries, pmid_prov)
        yield {"type": "log", "content": f"   👉 {len(papers_raw)}건 다운로드 완료 ({time.time()-start_t:.2f}초)"}

        # 4) Semantic rerank + topN
        qtext = " ".join(
            [t for t in [uq.target_hint, uq.disease, uq.organ, uq.intent, uq.hypothesis] if t]
        )
        yield {"type": "log", "content": f"🧠 의미 기반 랭킹(Semantic Ranking) 계산 중..."}
        papers_topn, _scores = self.ranker.rank(qtext, papers_raw, top_n=self.semantic_top_n)
        yield {"type": "log", "content": f"   👉 랭킹 상위 {len(papers_topn)}건 선정 완료"}

        # 5) keep/drop (optional)
        if self.use_llm_filter:
            yield {"type": "log", "content": "🤖 LLM 적합성 평가(Filter) 진행 중... (시간 소요)"}
            kept, _meta = self.filter.filter(uq, papers_topn)
            final_papers = kept
            yield {"type": "log", "content": f"   👉 최종 {len(final_papers)}건 통과"}
        else:
            final_papers = papers_topn
            yield {"type": "log", "content": "🤖 LLM 필터링 건너뜀 (설정: OFF)"}

        # 6) Output
        yield {"type": "log", "content": "✅ 모든 작업 완료! 결과 전송 중..."}
        
        # 최종 결과 객체 반환
        yield {"type": "result", "data": PaperCorpus(query_id=uq.query_id, papers=final_papers)}