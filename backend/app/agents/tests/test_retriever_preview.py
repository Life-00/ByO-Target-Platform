# ai/app/tests/test_retriever_preview.py
from app.agents.retriever.pipeline import RetrieverPipeline
from app.agents.retriever.query_expander import QueryExpander
from app.agents.retriever.pubmed_fetcher import PubMedFetcher
from app.agents.retriever.semantic_ranker import SemanticRanker
from app.agents.retriever.paper_filter import PaperFilter
from app.schemas.query import UserQuery
from _pytest.monkeypatch import MonkeyPatch


def _apply_mocks(mp):
    mp.setattr(QueryExpander, "expand",
               lambda self, uq: [{"query_id": "demo::q0", "query": "EGFR AND lung cancer", "reason": "keyword"}])
    mp.setattr(PubMedFetcher, "collect_pmids",
               lambda self, eqs, retmax=None: ({"demo::q0": ["1"]}, {"1": ["demo::q0"]}))
    mp.setattr(PubMedFetcher, "fetch_and_parse", lambda eqs, prov: [])
    mp.setattr(SemanticRanker, "rank", lambda self, q, papers, top_n=200: ([], {}))
    mp.setattr(PaperFilter, "filter", lambda self, uq, papers: (papers, {}))


def test_preview(monkeypatch, capsys):
    uq = UserQuery(
        query_id="demo",
        target_hint="EGFR",
        disease="lung cancer",
        organ="lung",
        intent="find therapeutic targets for lung cancer",
    )
    _apply_mocks(monkeypatch)
    corpus = RetrieverPipeline(use_llm_expand=False, use_llm_filter=False).run(uq)
    print("corpus:", corpus.model_dump())
    out, _ = capsys.readouterr()
    assert "corpus" in out


if __name__ == "__main__":
    mp = MonkeyPatch()
    try:
        _apply_mocks(mp)
        uq = UserQuery(
            query_id="demo",
            target_hint="EGFR",
            disease="lung cancer",
            organ="lung",
            intent="find therapeutic targets for lung cancer",
        )
        corpus = RetrieverPipeline(use_llm_expand=False, use_llm_filter=False).run(uq)
        print("corpus:", corpus.model_dump())
    finally:
        mp.undo()