import pytest
from app.schemas.paper import Paper
from app.schemas.fact import Fact
from app.schemas.claim import ValidatedClaim
from app.schemas.dossier import TargetDossier


@pytest.fixture
def sample_paper_corpus():
    return [
        Paper(
            pmid="123",
            title="EGFR inhibition in lung cancer",
            abstract="EGFR inhibition shows efficacy in lung cancer models.",
            journal="Nature",
            year="2020"
        )
    ]


@pytest.fixture
def sample_facts():
    return [
        Fact(
            pmid="123",
            sentence_id=0,
            text="EGFR inhibition reduces tumor growth",
            subject="EGFR",
            relation="inhibits",
            object="tumor growth"
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
