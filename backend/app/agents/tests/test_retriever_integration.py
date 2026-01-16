# ai/app/tests/test_retriever_pipeline.py
import json
import pytest

from app.agents.retriever.pipeline import RetrieverPipeline
from app.agents.retriever.query_expander import QueryExpander
from app.agents.retriever.pubmed_fetcher import PubMedFetcher
from app.agents.retriever.semantic_ranker import SemanticRanker
from app.agents.retriever.paper_filter import PaperFilter
from app.schemas.query import UserQuery, SearchConstraints
from app.schemas.retrieval import Paper, AbstractSentence


@pytest.fixture
def user_query():
    return UserQuery(
        query_id="q1",
        target_hint="EGFR",
        disease="lung cancer",
        organ="lung",
        intent="find therapeutic targets for lung cancer",
        hypothesis="EGFR resistance",
        constraints=SearchConstraints(max_results=3),
    )


@pytest.fixture
def sample_papers():
    return [
        Paper(
            pmid="1",
            title="EGFR study",
            abstract_sentences=[AbstractSentence(sentence_id="s0", text="EGFR improves outcomes.")],
            retrieval_reason="keyword",
            query_id="q1::q0",
        ),
        Paper(
            pmid="2",
            title="ALK study",
            abstract_sentences=[AbstractSentence(sentence_id="s1", text="ALK is oncogenic.")],
            retrieval_reason="keyword",
            query_id="q1::q1",
        ),
    ]


def test_query_expander_rule(user_query):
    expander = QueryExpander(use_llm=False)
    expanded = expander.expand(user_query)
    assert len(expanded) >= 1
    assert expanded[0]["query_id"].startswith("q1::")
    assert expanded[0]["reason"] == "keyword"


def test_pubmed_fetcher_collect_pmids(monkeypatch):
    calls = []

    def fake_search(term, n):
        calls.append((term, n))
        return ["10", "11"]

    monkeypatch.setattr("app.services.pubmed.client.search_pmids", fake_search)
    fetcher = PubMedFetcher(default_retmax=5)
    exp_queries = [{"query_id": "q1::q0", "query": "EGFR", "reason": "keyword"}]
    pmids_by_q, prov = fetcher.collect_pmids(exp_queries, retmax=2)
    assert pmids_by_q["q1::q0"] == ["10", "11"]
    assert prov == {"10": ["q1::q0"], "11": ["q1::q0"]}
    assert calls == [("EGFR", 2)]


def test_pubmed_fetcher_fetch_and_parse(monkeypatch):
    def fake_fetch(pmid):
        return f"PMID- {pmid}\nTI  - EGFR title\nAB  - EGFR improves outcomes.\nDP  - 2020\nJT  - Nature\n"

    monkeypatch.setattr("app.services.pubmed.client.fetch_medline", fake_fetch)
    exp_queries = [{"query_id": "q1::q0", "query": "EGFR", "reason": "keyword"}]
    papers = PubMedFetcher.fetch_and_parse(exp_queries, {"123": ["q1::q0"]})
    assert papers[0].pmid == "123"
    assert papers[0].title == "EGFR title"
    assert papers[0].year == 2020
    assert papers[0].retrieval_reason == "keyword"


def test_semantic_ranker(monkeypatch, sample_papers):
    class FakeEmb:
        def __call__(self, docs):
            return [[1.0, 0.0], [0.0, 1.0]]

        def embed_query(self, q):
            return [1.0, 0.0]

    monkeypatch.setattr("app.agents.retriever.semantic_ranker.UpstageChromaEmbedding", lambda: FakeEmb())
    ranker = SemanticRanker(use_knee_cutoff=False)
    top, scores = ranker.rank("EGFR", sample_papers, top_n=1)
    assert len(top) == 1
    assert top[0].pmid == "1"
    assert scores["1"] > scores["2"]


def test_paper_filter(monkeypatch, user_query, sample_papers):
    # deterministic LLM reply
    class FakeResp:
        class Choice:
            class Msg:
                def __init__(self, content):
                    self.content = content

            def __init__(self, content):
                self.message = self.Msg(content)

        def __init__(self, content):
            self.choices = [self.Choice(content)]

    def fake_create(**kwargs):
        payload = json.loads(kwargs["messages"][1]["content"])
        title = payload["paper"]["title"]
        decision = "KEEP" if "EGFR" in title else "DROP"
        return FakeResp(json.dumps({"decision": decision, "confidence": 0.9, "reasons": ["test"]}))

    monkeypatch.setattr("app.core.llm.llm_client.chat.completions.create", fake_create)
    filt = PaperFilter(keep_eval_n=10, keep_uncertain=False, keep_remaining=False)
    kept, meta = filt.filter(user_query, sample_papers)
    assert [p.pmid for p in kept] == ["1"]
    assert meta["1"]["decision"] == "KEEP"
    assert meta["2"]["decision"] == "DROP"


def test_retriever_pipeline_integration(monkeypatch, user_query, sample_papers):
    # Mock subcomponents to avoid network/LLM
    monkeypatch.setattr(QueryExpander, "expand", lambda self, uq: [{"query_id": "q1::q0", "query": "EGFR", "reason":
        "keyword"}])
    monkeypatch.setattr(PubMedFetcher, "collect_pmids", lambda self, eqs, retmax=None: ({"q1::q0": ["1"]}, {"1":
                                                                                                                ["q1::q0"]}))
    monkeypatch.setattr(PubMedFetcher, "fetch_and_parse", lambda eqs, prov: [sample_papers[0]])
    monkeypatch.setattr(SemanticRanker, "rank", lambda self, qtext, papers, top_n=200: (papers, {"1": 1.0}))
    monkeypatch.setattr(PaperFilter, "filter", lambda self, uq, papers: (papers, {}))

    pipeline = RetrieverPipeline(use_llm_expand=False, use_llm_filter=True, default_retmax=3, semantic_top_n=5)
    corpus = pipeline.run(user_query)

    assert corpus.query_id == "q1"
    assert len(corpus.papers) == 1
    assert corpus.papers[0].pmid == "1"