from app.agents.extractor.agent import ExtractorAgent

def test_extractor_produces_facts(sample_paper_corpus):

    agent = ExtractorAgent()
    facts = agent.run(sample_paper_corpus)

    assert facts is not None
    assert len(facts.facts) > 0