from app.agents.retriever.agent import RetrieverAgent
from app.schemas.user_query import UserQuery, SearchConstraints

def test_retriever_returns_paper_corpus():
    agent = RetrieverAgent()
    uq = UserQuery(
        query_id="test",
        target="EGFR",
        disease="lung cancer",
        organ="lung",
        research_question="Is EGFR a valid therapeutic target?",
        constraints=SearchConstraints(year_from=2018)
    )

    corpus = agent.run(uq)

    assert corpus is not None
    assert len(corpus.papers) > 0