# app/agents/synthesizer/assembler.py
from typing import List, Dict, Set, Any, Tuple
from collections import defaultdict
from app.schemas.vector_hit import VectorHit
from app.schemas.dossier import TargetDossier, DossierSection

# 근거 수준 우선순위 정의
EVIDENCE_PRIORITY = {"clinical": 0, "in_vivo": 1, "in_vitro": 2}
MAX_CLAIMS = 10

def _collect_pmids(hit: VectorHit) -> Set[str]:
    pmids = {hit.paper.pmid} if hit.paper and hit.paper.pmid else set()
    for c in hit.evidence: 
        if c.pmid: pmids.add(c.pmid)
    return pmids

def build_dossier_sections(user_query: str, hits: List[VectorHit], user_context: str = "") -> TargetDossier:
    """
    데이터 정렬 및 섹션 조립 로직을 수행합니다.
    """
    print(f"[Assembler] Processing {len(hits)} knowledge chunks...")

    # 1. 정렬: 검색 순위 -> 근거 수준 -> 발행 연도
    hits_sorted = sorted(hits, key=lambda h: (
        h.retrieval.get("rank", 999) if h.retrieval else 999,
        EVIDENCE_PRIORITY.get(h.evidence_level, 99),
        -(h.paper.year if h.paper and h.paper.year else 0)
    ))

    # 2. 섹션 데이터 구성
    sections = {}
    ev_map = defaultdict(list)
    for h in hits_sorted: ev_map[h.evidence_level].append(h.claim_id)
    
    # [Target Profile]
    papers = sorted({h.paper.pmid for h in hits_sorted if h.paper and h.paper.pmid})
    profile_text = f"- 질의어: {user_query}\n- 분석 논문 수: {len(papers)}건\n- 추출된 주장 수: {len(hits_sorted)}건"
    sections["target_profile"] = [DossierSection(text=profile_text, citations=papers)]

    # [Key Claims]
    sections["key_claims"] = [
        DossierSection(
            text=f"### [주장 {h.claim_id}]\n- 내용: {h.claim_text}\n- 근거 수준: {h.evidence_level}\n- 인용구: \"{h.evidence[0].quote if h.evidence else ''}\"",
            citations=list(_collect_pmids(h))
        ) for h in hits_sorted[:MAX_CLAIMS]
    ]

    # [Evidence Summary]
    ev_summary = "\n".join([f"- {k}: {len(v)}건" for k, v in ev_map.items()])
    sections["evidence_level_summary"] = [DossierSection(text=ev_summary, citations=[])]

    # [Risk Signals]
    risks = []
    for h in hits_sorted:
        for r in h.risk_signals:
            risks.append(DossierSection(text=f"- 위험 유형: {r.type}\n- 근거: {r.citation.quote}", citations=[r.citation.pmid]))
    sections["risk_signals"] = risks

    # [Next Validation Steps] (Gap 분석)
    steps = []
    if "clinical" not in ev_map: steps.append("- 임상(Clinical) 데이터 공백: 추가적인 임상 문헌 검토 또는 설계가 필요합니다.")
    if "in_vivo" not in ev_map: steps.append("- 동물 실험(In vivo) 데이터 보완: 생체 내 효능 검증 데이터가 부족합니다.")
    sections["next_validation_steps"] = [DossierSection(text="\n".join(steps) or "- 모든 근거 단계가 식별되었습니다.", citations=[])]

    return TargetDossier(dossier_id="doc_01", target=user_query, sections=sections, format="markdown")