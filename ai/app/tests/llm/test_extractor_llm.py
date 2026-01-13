# app/tests/extractor/test_extractor_llm.py
import pytest

from app.agents.extractor.agent import ExtractorAgent
from app.schemas.paper import Paper, AbstractSentence


@pytest.mark.integration
def test_extractor_llm_relation_smoke():
    """
    목적:
    - extractor 전체 파이프라인이 LLM 포함 상태로 정상 동작하는지
    - relation이 unknown이 아닌 값으로 추출되는지
    """

    # 더미 논문 데이터
    paper = Paper(
        pmid="12345678",
        title="EGFR inhibition in lung cancer",
        year=2023,
        journal="Nature Medicine",
        abstract_sentences=[
            AbstractSentence(
                sentence_id="s1",
                text="EGFR inhibition significantly reduced tumor growth in lung cancer mouse models."
            )
        ],
        retrieval_reason="EGFR lung cancer target validation"
    )

    agent = ExtractorAgent()

    fact_set = agent.run([paper])

    assert len(fact_set.facts) == 1
    fact = fact_set.facts[0]
    assert fact.relation is not None

    # LLM이 의미 있는 관계를 추출했는지
    assert fact.relation.effect != "unknown"
    assert fact.relation.stance != "unknown"