from __future__ import annotations

from app.schemas.query import UserQuery
from app.schemas.retrieval import PaperCorpus

from app.agents.retriever.query_expander import QueryExpander
from app.agents.retriever.multi_source_fetcher import MultiSourceFetcher
from app.agents.retriever.adapters import (
    PubMedAdapter,
    EuropePmcAdapter,
    CrossrefAdapter,
    ArxivAdapter,
)
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
        self.default_retmax = default_retmax
        self.fetcher = MultiSourceFetcher(
            adapters=[
                PubMedAdapter(default_retmax=default_retmax),
                EuropePmcAdapter(page_size=default_retmax, oa_only=True),
                CrossrefAdapter(default_retmax=default_retmax, oa_only=True),
                ArxivAdapter(default_retmax=default_retmax),
            ]
        )
        self.ranker = SemanticRanker(
            use_knee_cutoff=use_knee_cutoff,
            knee_min_k=knee_min_k,
            knee_max_k=knee_max_k or semantic_top_n,
        )
        self.filter = PaperFilter(keep_eval_n=llm_keep_eval_n)

        self.use_llm_filter = use_llm_filter
        self.semantic_top_n = semantic_top_n

    def run_stream(self, uq: UserQuery):
        # 1) Query expansion
        yield {"type": "log", "content": f"🔄 쿼리 확장 시작 (ID: {uq.query_id})"}
        expanded_queries = self.expander.expand(uq)
        yield {"type": "log", "content": f"   ✅ 확장 쿼리 {len(expanded_queries)}개 생성"}

        # 2) Multi-source fetch
        retmax = None
        if getattr(uq, "constraints", None) is not None:
            retmax = getattr(uq.constraints, "max_results", None)

        yield {"type": "log", "content": f"🔎 멀티소스 검색 실행 (max/source: {retmax or self.default_retmax})"}
        papers_raw = self.fetcher.fetch(expanded_queries, retmax=retmax)
        yield {"type": "log", "content": f"   ✅ {len(papers_raw)}편 수집 (PubMed/Europe PMC/Crossref/arXiv)"}

        if not papers_raw:
            yield {"type": "log", "content": "⚠️ 검색 결과가 없습니다. 프로세스 종료."}
            yield {"type": "result", "data": PaperCorpus(query_id=uq.query_id, papers=[])}
            return

        # 3) Semantic rerank + topN
        qtext = " ".join([t for t in [uq.target_hint, uq.disease, uq.organ, uq.intent, uq.hypothesis] if t])
        yield {"type": "log", "content": "🧠 의미 기반 랭킹 계산 중..."}
        papers_topn, _scores = self.ranker.rank(qtext, papers_raw, top_n=self.semantic_top_n)
        yield {"type": "log", "content": f"   ✅ 상위 {len(papers_topn)}편 선택"}

        # 4) keep/drop (optional)
        if self.use_llm_filter:
            yield {"type": "log", "content": "🧹 LLM 필터링 진행 중...(시간 소요)"}
            kept, _meta = self.filter.filter(uq, papers_topn)
            final_papers = kept
            yield {"type": "log", "content": f"   ✅ 최종 {len(final_papers)}편 남김"}
        else:
            final_papers = papers_topn
            yield {"type": "log", "content": "ℹ️ LLM 필터 비활성화 상태"}

        # 5) Output
        yield {"type": "log", "content": "📦 결과 반환"}
        yield {"type": "result", "data": PaperCorpus(query_id=uq.query_id, papers=final_papers)}

    def run(self, uq: UserQuery) -> PaperCorpus:
        """
        Convenience wrapper to run the generator and return the final corpus.
        """
        result: PaperCorpus | None = None
        for step in self.run_stream(uq):
            if step.get("type") == "result":
                result = step["data"]
        return result or PaperCorpus(query_id=uq.query_id, papers=[])
