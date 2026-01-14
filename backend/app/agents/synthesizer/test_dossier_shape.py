from app.agents.synthesizer.agent import SynthesizerAgentV2
from app.schemas.vector_hit import VectorHit, PaperMeta, Citation
from app.schemas.dossier import TargetDossier

def _make_valid_hit(claim_id: str) -> VectorHit:
    return VectorHit(
        claim_id=claim_id,
        claim_text="A affects B",
        relation_type="associates",
        entities={},
        evidence_level="in_vitro",
        evidence=[
            Citation(
                pmid="123456",
                url="https://pubmed.ncbi.nlm.nih.gov/123456/",
                quote="This study shows A affects B."
            )
        ],
        risk_signals=[],
        paper=PaperMeta(
            pmid="123456",
            title="Test paper",
            year=2024,
            url="https://pubmed.ncbi.nlm.nih.gov/123456/"
        ),
        retrieval={}
    )

def test_synthesizer_returns_target_dossier():
    agent = SynthesizerAgentV2()
    hits = [_make_valid_hit("C1"), _make_valid_hit("C2")]

    dossier = agent.run(user_query="Test Target", hits=hits)

    # 1) 타입 확인
    assert isinstance(dossier, TargetDossier)

    # 2) 고정 섹션 키 존재 확인
    expected_sections = {
        "target_profile",
        "key_claims",
        "evidence_level_summary",
        "risk_signals",
        "next_validation_steps",
    }
    assert expected_sections.issubset(set(dossier.sections.keys()))

    # 3) Key claims 구조 확인
    key_claims = dossier.sections["key_claims"]
    assert len(key_claims) == 2

    for section in key_claims:
        assert isinstance(section.text, str)
        assert section.text.strip() != ""
        assert isinstance(section.citations, list)
        assert len(section.citations) > 0
