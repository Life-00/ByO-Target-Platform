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
        # 1) Query expansion
        expanded_queries = self.expander.expand(uq)

        # 2) Collect PMIDs (retmax: constraints 우선)
        retmax = None
        if getattr(uq, "constraints", None) is not None:
            retmax = getattr(uq.constraints, "max_results", None)

        _, pmid_prov = self.fetcher.collect_pmids(expanded_queries, retmax=retmax)

        # 3) Fetch + parse
        papers_raw = self.fetcher.fetch_and_parse(expanded_queries, pmid_prov)

        # 4) Semantic rerank + topN
        qtext = " ".join(
            [t for t in [uq.target_hint, uq.disease, uq.organ, uq.intent, uq.hypothesis] if t]
        )
        papers_topn, _scores = self.ranker.rank(qtext, papers_raw, top_n=self.semantic_top_n)

        # 5) keep/drop (optional)
        if self.use_llm_filter:
            kept, _meta = self.filter.filter(uq, papers_topn)
            final_papers = kept
        else:
            final_papers = papers_topn

        # 6) Output
        return PaperCorpus(query_id=uq.query_id, papers=final_papers)
