# app/tests/test_report_agent_contract.py
import pytest

from app.agents.synthesizer.agent import SynthesizerAgentV2
from app.schemas.vector_hit import VectorHit, PaperMeta, Citation
from app.schemas.dossier import TargetDossier, DossierSection

from app.agents.synthesizer.post_validate import post_validate_dossier, PostValidateError


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


def test_hits_empty_returns_cannot_say_report_and_keeps_schema_keys():
    agent = SynthesizerAgentV2()
    dossier = agent.run(user_query="Test Target", hits=[], user_context="context")

    assert isinstance(dossier, TargetDossier)

    expected_sections = {
        "target_profile",
        "key_claims",
        "evidence_level_summary",
        "risk_signals",
        "next_validation_steps",
    }
    assert expected_sections.issubset(set(dossier.sections.keys()))

    # cannot_say_report 특징(assembler 텍스트 기반)
    tp = dossier.sections["target_profile"]
    assert len(tp) == 1
    assert "분석 논문 수: 0건" in (tp[0].text or "")
    assert "추출된 주장 수: 0건" in (tp[0].text or "")

    # hits=0이면 key_claims/risk_signals는 비어도 허용
    assert dossier.sections["key_claims"] == []
    assert dossier.sections["risk_signals"] == []

    # next_validation_steps는 최소 텍스트를 가져야 함
    nvs = dossier.sections["next_validation_steps"]
    assert len(nvs) == 1
    assert (nvs[0].text or "").strip() != ""


def test_post_validate_catches_broken_key_claims_evidence_format():
    # 스키마는 유지하되, key_claims 텍스트에서 evidence markers를 일부러 깨뜨린 dossier 생성
    broken = TargetDossier(
        dossier_id="doc_x",
        target="T",
        sections={
            "target_profile": [DossierSection(text="ok", citations=[])],
            "key_claims": [DossierSection(text="### claim\n- 내용: X\n(no evidence here)", citations=["123"])],
            "evidence_level_summary": [DossierSection(text="ok", citations=[])],
            "risk_signals": [],
            "next_validation_steps": [DossierSection(text="ok", citations=[])],
        },
        format="markdown",
    )

    with pytest.raises(PostValidateError):
        post_validate_dossier(broken)


def test_post_validate_passes_for_normal_report():
    agent = SynthesizerAgentV2()
    hits = [_make_valid_hit("C1"), _make_valid_hit("C2")]
    dossier = agent.run(user_query="Test Target", hits=hits, user_context="context")

    # run() 내부에서 post_validate를 이미 통과해야 함
    assert isinstance(dossier, TargetDossier)
    assert len(dossier.sections["key_claims"]) == 2

def test_post_validate_catches_empty_pmid_or_url_in_source_line():
    broken = TargetDossier(
        dossier_id="doc_x2",
        target="T",
        sections={
            "target_profile": [DossierSection(text="ok", citations=[])],
            "key_claims": [
                DossierSection(
                    text="\n".join([
                        "### [주장 C1]",
                        "- 내용: X",
                        "- 근거 수준: in_vitro",
                        "- Evidence:",
                        '- Quote: "something"',
                        "  Source: PMID:  | https://pubmed.ncbi.nlm.nih.gov/123456/",  # pmid empty
                    ]),
                    citations=["123456"],
                )
            ],
            "evidence_level_summary": [DossierSection(text="ok", citations=[])],
            "risk_signals": [],
            "next_validation_steps": [DossierSection(text="ok", citations=[])],
        },
        format="markdown",
    )

    with pytest.raises(PostValidateError):
        post_validate_dossier(broken)
