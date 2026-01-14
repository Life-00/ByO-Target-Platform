#!/usr/bin/env bash
set -euo pipefail

ROOT="ai/app"
SYN="$ROOT/agents/synthesizer_v2"
SCHEMA="$ROOT/schemas"
TESTS="ai/app/tests/synthesizer_v2"

mkdir -p "$SYN" "$SCHEMA" "$TESTS"

cat > "$SCHEMA/citation.py" << 'PY'
from pydantic import BaseModel

class Citation(BaseModel):
    pmid: str
    url: str
    quote: str
    section: str | None = None
PY

cat > "$SCHEMA/vector_hit.py" << 'PY'
from pydantic import BaseModel
from typing import List, Dict, Any
from .citation import Citation

class PaperMeta(BaseModel):
    pmid: str
    title: str
    year: int | None = None
    url: str

class RiskSignal(BaseModel):
    type: str
    citation: Citation

class VectorHit(BaseModel):
    claim_id: str
    claim_text: str
    relation_type: str | None = None
    entities: Dict[str, Any] = {}
    evidence_level: str
    evidence: List[Citation]
    risk_signals: List[RiskSignal] = []
    paper: PaperMeta
    retrieval: Dict[str, Any] = {}
PY

cat > "$SYN/guards.py" << 'PY'
from typing import List
from app.schemas.vector_hit import VectorHit

class GuardError(ValueError):
    pass

def validate_hits(hits: List[VectorHit]) -> None:
    if not hits:
        raise GuardError("No vector hits provided")

    for h in hits:
        if not h.claim_text.strip():
            raise GuardError(f"Empty claim_text: {h.claim_id}")

        if not h.evidence:
            raise GuardError(f"Missing evidence: {h.claim_id}")

        for c in h.evidence:
            if not c.quote.strip():
                raise GuardError(f"Empty evidence quote: {h.claim_id}")
            if not c.pmid.strip() or not c.url.strip():
                raise GuardError(f"Missing citation fields: {h.claim_id}")

        for r in h.risk_signals:
            cit = r.citation
            if not cit.quote.strip() or not cit.pmid.strip() or not cit.url.strip():
                raise GuardError(f"Risk signal without citation: {h.claim_id}")
PY

cat > "$SYN/assembler.py" << 'PY'
from typing import List, Dict
from collections import defaultdict
from app.schemas.vector_hit import VectorHit

def build_dossier_skeleton(user_query: str, hits: List[VectorHit]) -> Dict:
    years = [h.paper.year for h in hits if h.paper.year is not None]
    profile = {
        "query": user_query,
        "coverage": {
            "papers": len({h.paper.pmid for h in hits}),
            "claims": len(hits),
            "years": {"min": min(years) if years else None, "max": max(years) if years else None},
        },
    }

    grouped = defaultdict(list)
    for h in hits:
        grouped[h.relation_type or "unknown"].append(h)

    key_claims = []
    for rel, items in grouped.items():
        for h in items:
            key_claims.append({
                "relation_type": rel,
                "claim_id": h.claim_id,
                "claim_text": h.claim_text,
                "evidence": [{"quote": c.quote, "pmid": c.pmid, "url": c.url} for c in h.evidence],
            })

    evidence_level = defaultdict(list)
    for h in hits:
        evidence_level[h.evidence_level].append(h.claim_id)

    risks = []
    for h in hits:
        for r in h.risk_signals:
            risks.append({
                "claim_id": h.claim_id,
                "risk_type": r.type,
                "evidence": {"quote": r.citation.quote, "pmid": r.citation.pmid, "url": r.citation.url},
            })

    next_steps = []
    if len(evidence_level.get("clinical", [])) == 0:
        next_steps.append({"proposal": "임상(Clinical) 근거가 부족하여 임상 단계 데이터/연구 설계 검토가 필요", "supported_by": "gap:clinical_empty"})
    if len(evidence_level.get("in_vivo", [])) == 0:
        next_steps.append({"proposal": "동물(In vivo) 근거가 부족하여 in vivo 단계 검증이 필요", "supported_by": "gap:in_vivo_empty"})

    return {
        "target_profile": profile,
        "key_claims": key_claims,
        "evidence_level": dict(evidence_level),
        "risk_signals": risks,
        "next_validation_steps": next_steps,
    }
PY

cat > "$SYN/prompts.py" << 'PY'
FORMAT_PROMPT = """\
역할: 너는 '리포트 편집자'다. 아래 FACTS_WITH_CITATIONS에 포함된 내용만 사용해 Target Dossier를 보기 좋게 정리하라.

절대 금지:
- 제공되지 않은 새로운 사실/주장/해석 생성
- 근거(quote) 없이 문장 작성
- pmid/url 없는 인용 생성
- 여러 근거를 임의로 일반화/뭉뚱그려 단정 문장 만들기

출력 규칙:
- 각 Claim 블록은 반드시 Evidence(quote+PMID+URL)를 포함한다.
- Evidence의 quote/PMID/URL은 원문 그대로 유지(변형 금지).
- Risk Signals는 근거가 있을 때만 작성한다.
- Next Validation Steps는 근거 공백(gap)에 근거한 제안 수준으로만 작성한다(결론 금지).

[USER_CONTEXT]
{user_context}

[FACTS_WITH_CITATIONS]
{facts}

출력 섹션:
1) Target Profile
2) Key Claims (각 claim마다 Evidence 필수)
3) Evidence Level (in vitro / in vivo / clinical)
4) Risk Signals (근거 있을 때만)
5) Next Validation Steps (제안 수준)
"""
PY

cat > "$SYN/renderer.py" << 'PY'
import json
from app.core.llm import generate_text
from .prompts import FORMAT_PROMPT

def render_dossier(user_context: str, skeleton: dict) -> str:
    facts = json.dumps(skeleton, ensure_ascii=False, indent=2)
    prompt = FORMAT_PROMPT.format(user_context=user_context, facts=facts)
    return generate_text(prompt)
PY

cat > "$SYN/agent.py" << 'PY'
from typing import List
from app.schemas.vector_hit import VectorHit
from .guards import validate_hits
from .assembler import build_dossier_skeleton
from .renderer import render_dossier

class SynthesizerAgentV2:
    def run(self, user_query: str, hits: List[VectorHit], user_context: str = "") -> str:
        validate_hits(hits)
        skeleton = build_dossier_skeleton(user_query=user_query, hits=hits)
        return render_dossier(user_context=user_context, skeleton=skeleton)
PY

touch "$SYN/__init__.py"
mkdir -p "$TESTS"
touch "$TESTS/__init__.py"

cat > "$TESTS/test_guards.py" << 'PY'
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
PY

echo "✅ Synthesizer V2 scaffold created."
