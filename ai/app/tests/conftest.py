import pytest
from app.schemas.paper import Paper, AbstractSentence
from app.schemas.fact import Fact, RelationInfo, EntitySet, ExperimentInfo
from app.schemas.claim import ValidatedClaim
from app.schemas.dossier import TargetDossier


@pytest.fixture
def sample_paper_corpus():
    return [
        Paper(
            pmid="123",
            title="EGFR inhibition in lung cancer",
            abstract="EGFR inhibition shows efficacy in lung cancer models.",
            abstract_sentences=[
                AbstractSentence(
                    sentence_id="s0",
                    text="EGFR inhibition shows efficacy in lung cancer models."
                )
            ],
            journal="Nature",
            year="2020",
            retrieval_reason="test_fixture"
        )
    ]


@pytest.fixture
def sample_facts():
    return [
        Fact(
            fact_id="f1",
            pmid="123",
            sentence_id="s0",
            text="EGFR inhibition reduces tumor growth",
            entities=EntitySet(
                target=["EGFR"],
                disease=["lung cancer"],
                organ=[],
                compound=[]
            ),
            relation=RelationInfo(
                type="decrease",
                object="tumor growth"
            ),
            experiment=ExperimentInfo(
                model="animal",
                species="mouse"
            )
        )
    ]


@pytest.fixture
def sample_validated_claims():
    return [
        ValidatedClaim(
            claim_id="c1",
            normalized_claim="EGFR inhibits tumor growth",
            evidence=[],
            evidence_summary={},
            consistency="consistent",
            risk_signals=[]
        )
    ]
