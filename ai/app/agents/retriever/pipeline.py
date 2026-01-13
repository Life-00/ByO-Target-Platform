# app/agents/retriever/pipeline.py
from __future__ import annotations

from typing import Dict, List, Optional

from app.schemas.query import UserQuery
from app.schemas.retrieval import PaperCorpus, Paper

from app.agents.retriever.query_expander import QueryExpander
from app.agents.retriever.pubmed_fetcher import PubMedFetcher
from app.agents.retriever.semantic_ranker import SemanticRanker
from app.agents.retriever.paper_filter import PaperFilter


class RetrieverPipeline:
    def __init__(
        self,
        use_llm_expand: bool = False,
        use_llm_filter: bool = True,
        default_retmax: int = 50,
        semantic_top_n: int = 200,
        llm_keep_eval_n: int = 80,
    ):
        self.expander = QueryExpander(use_llm=use_llm_expand)
        self.fetcher = PubMedFetcher(default_retmax=default_retmax)
        self.ranker = SemanticRanker()
        self.use_llm_filter = use_llm_filter
        self.semantic_top_n = semantic_top_n
        self.filter = PaperFilter(keep_eval_n=llm_keep_eval_n)

    def run(self, uq: UserQuery) -> PaperCorpus:
        # 1) 쿼리 확장
        expanded_queries = self.expander.expand(uq)

        # 2) PMID 수집(확장쿼리 합집합)
        retmax = uq.constraints.max_results if (uq.constraints and uq.constraints.max_results) else None
        _, pmid_prov = self.fetcher.collect_pmids(expanded_queries, retmax=retmax)

        # 3) fetch + parse (Paper 생성, query_id/retrieval_reason 주입)
        papers_raw = self.fetcher.fetch_and_parse(expanded_queries, pmid_prov)

        # 4) 의미 기반 축소 (embedding rerank + topN)
        qtext = " ".join([t for t in [uq.target_hint, uq.disease, uq.organ, uq.intent, uq.hypothesis] if t])
        papers_topn, _scores = self.ranker.rank(qtext, papers_raw, top_n=self.semantic_top_n)

        # 5) keep/drop (선택)
        if self.use_llm_filter:
            kept, _meta = self.filter.filter(uq, papers_topn)
            final_papers = kept
        else:
            final_papers = papers_topn

        # 6) PaperCorpus 반환
        return PaperCorpus(query_id=uq.query_id, papers=final_papers)
