# ai/app/agents/synthesizer_v2/assembler.py
from typing import List, Dict, Set
from collections import defaultdict
from app.schemas.vector_hit import VectorHit
from app.schemas.dossier import TargetDossier, DossierSection

def _collect_pmids_from_hit(hit: VectorHit) -> Set[str]:
    pmids: Set[str] = set()
    # claim evidence
    for c in hit.evidence:
        if c.pmid:
            pmids.add(c.pmid)
    # risk evidence
    for r in hit.risk_signals:
        if r.citation and r.citation.pmid:
            pmids.add(r.citation.pmid)
    # paper meta
    if hit.paper and hit.paper.pmid:
        pmids.add(hit.paper.pmid)
    return pmids

def _fmt_evidence_lines(hit: VectorHit) -> str:
    lines = []
    for c in hit.evidence:
        # quote/url은 text에, citations에는 pmid만!
        lines.append(f'- Quote: "{c.quote}"')
        lines.append(f'  Source: PMID: {c.pmid} | {c.url}')
    return "\n".join(lines)

def _fmt_risk_lines(hit: VectorHit) -> str:
    if not hit.risk_signals:
        return ""
    lines = []
    for r in hit.risk_signals:
        cit = r.citation
        lines.append(f'- Risk: {r.type}')
        lines.append(f'  Evidence: "{cit.quote}"')
        lines.append(f'  Source: PMID: {cit.pmid} | {cit.url}')
    return "\n".join(lines)

def build_dossier_sections(user_query: str, hits: List[VectorHit], user_context: str = "") -> TargetDossier:
    # --- coverage 요약 ---
    papers = sorted({h.paper.pmid for h in hits if h.paper and h.paper.pmid})
    years = [h.paper.year for h in hits if h.paper and h.paper.year is not None]
    year_min = min(years) if years else None
    year_max = max(years) if years else None

    # --- evidence level summary ---
    ev = defaultdict(list)
    for h in hits:
        ev[h.evidence_level].append(h.claim_id)

    # --- 고정 섹션: Target Profile ---
    profile_text = "\n".join([
        f"- Query: {user_query}",
        f"- Coverage: papers={len(papers)}, claims={len(hits)}, years={year_min}~{year_max}",
        f"- Notes: {'(user_context provided)' if user_context else '(none)'}",
    ])
    profile_pmids = papers[:] 
    target_profile_section = DossierSection(text=profile_text, citations=profile_pmids)

    # --- 고정 섹션: Key Claims (각 claim은 섹션 1개로) ---
    key_claim_sections: List[DossierSection] = []
    for h in hits:
        claim_text = "\n".join([
            f"### Claim {h.claim_id}",
            f"- Claim: {h.claim_text}",
            f"- Relation: {h.relation_type}",
            f"- Evidence level: {h.evidence_level}",
            f"- Evidence:",
            _fmt_evidence_lines(h),
        ])
        pmids = sorted(_collect_pmids_from_hit(h))
        key_claim_sections.append(DossierSection(text=claim_text, citations=pmids))

    # --- 고정 섹션: Evidence Level Summary ---
    ev_text = "\n".join([
        f"- in_vitro: {len(ev.get('in_vitro', []))} claim(s) -> {ev.get('in_vitro', [])}",
        f"- in_vivo: {len(ev.get('in_vivo', []))} claim(s) -> {ev.get('in_vivo', [])}",
        f"- clinical: {len(ev.get('clinical', []))} claim(s) -> {ev.get('clinical', [])}",
    ])
    ev_pmids = papers[:]
    evidence_level_section = DossierSection(text=ev_text, citations=ev_pmids)

    # --- 고정 섹션: Risk Signals (있는 것만) ---
    risk_sections: List[DossierSection] = []
    for h in hits:
        if not h.risk_signals:
            continue
        risk_text = "\n".join([
            f"### Risks for Claim {h.claim_id}",
            _fmt_risk_lines(h),
        ])
        pmids = sorted(_collect_pmids_from_hit(h))
        risk_sections.append(DossierSection(text=risk_text, citations=pmids))

    # --- 고정 섹션: Next Validation Steps (gap 기반만) ---
    next_steps_lines = []
    if len(ev.get("clinical", [])) == 0:
        next_steps_lines.append("- Step: 임상(Clinical) 근거가 부족 → 임상 단계 데이터/연구 설계 검토 필요 (gap:clinical_empty)")
    if len(ev.get("in_vivo", [])) == 0:
        next_steps_lines.append("- Step: 동물(In vivo) 근거가 부족 → in vivo 단계 검증 필요 (gap:in_vivo_empty)")
    if not next_steps_lines:
        next_steps_lines.append("- (No suggested steps based on evidence gaps)")

    next_steps_section = DossierSection(text="\n".join(next_steps_lines), citations=papers[:])

    # --- TargetDossier 최종 조립 ---
    sections: Dict[str, List[DossierSection]] = {
        "target_profile": [target_profile_section],
        "key_claims": key_claim_sections,
        "evidence_level_summary": [evidence_level_section],
        "risk_signals": risk_sections,
        "next_validation_steps": [next_steps_section],
    }

    return TargetDossier(
        dossier_id="temp",   # 실제 id는 orchestrator/서비스에서 넣어도 됨
        target=user_query,   # 혹은 target 이름 따로 있으면 그걸 사용
        sections=sections,
        format="markdown",
    )
