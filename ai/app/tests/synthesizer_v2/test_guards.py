from app.agents.synthesizer_v2.guards import validate_hits, GuardError
from app.schemas.vector_hit import VectorHit, PaperMeta, Citation

def test_validate_hits_rejects_missing_evidence():
    hit = VectorHit(
        claim_id="C1",
        claim_text="A affects B",
        relation_type="associates",
        entities={},
        evidence_level="in_vitro",
        evidence=[],
        paper=PaperMeta(pmid="1", title="t", year=2024, url="u"),
        retrieval={}
    )
    try:
        validate_hits([hit])
        assert False, "Should have raised GuardError"
    except GuardError:
        assert True

def test_validate_hits_accepts_valid_hit():
    hit = VectorHit(
        claim_id="C2",
        claim_text="A affects B",
        relation_type="associates",
        entities={},
        evidence_level="in_vitro",
        evidence=[Citation(pmid="1", url="u", quote="Evidence sentence")],
        paper=PaperMeta(pmid="1", title="t", year=2024, url="u"),
        retrieval={}
    )
    validate_hits([hit])
