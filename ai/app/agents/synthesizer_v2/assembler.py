# ai/app/agents/synthesizer_v2/assembler.py
from typing import List, Dict, Set, Any, Tuple
from collections import defaultdict
from app.schemas.vector_hit import VectorHit
from app.schemas.dossier import TargetDossier, DossierSection

# -----------------------------
# evidence_level 우선순위
# clinical > in_vivo > in_vitro
# -----------------------------
EVIDENCE_PRIORITY = {
    "clinical": 0,
    "in_vivo": 1,
    "in_vitro": 2,
}


# Step3: Top-K 제한
MAX_CLAIMS = 10


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
    lines: List[str] = []
    for c in hit.evidence:
        # quote/url은 text에, citations에는 pmid만!
        lines.append(f'- Quote: "{c.quote}"')
        lines.append(f'  Source: PMID: {c.pmid} | {c.url}')
    return "\n".join(lines) if lines else "- (No evidence provided)"


def _fmt_risk_lines(hit: VectorHit) -> str:
    if not hit.risk_signals:
        return "- (No risk signals)"

    lines: List[str] = []
    for r in hit.risk_signals:
        cit = r.citation
        lines.append(f"- Risk: {r.type}")
        lines.append(f'  Evidence: "{cit.quote}"')
        lines.append(f"  Source: PMID: {cit.pmid} | {cit.url}")
    return "\n".join(lines)


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _rank_key(hit: VectorHit) -> Tuple[int, int]:
    """
    Step2: retrieval 우선순위
    - retrieval.rank 가 있으면 (작을수록 상위)
    - 없으면 retrieval.score 가 있으면 (클수록 상위)
    - 둘 다 없으면 마지막
    """
    r = hit.retrieval or {}

    if r.get("rank") is not None:
        return (0, _safe_int(r.get("rank"), 999999))

    if r.get("score") is not None:
        # score는 큰 값이 상위 → 음수로 뒤집어서 오름차순 정렬
        return (1, -_safe_int(_safe_float(r.get("score"), 0.0) * 1000, 0))

    return (2, 0)


def _evidence_key(hit: VectorHit) -> int:
    return EVIDENCE_PRIORITY.get(hit.evidence_level, 99)


def _year_key(hit: VectorHit) -> int:
    if hit.paper and hit.paper.year is not None:
        return -_safe_int(hit.paper.year, 0)  # 최신이 먼저
    return 0


def build_dossier_sections(user_query: str, hits: List[VectorHit], user_context: str = "") -> TargetDossier:
    """
    Synthesizer v2 (Step1~Step4 반영)
    - Step1: 섹션 키(목차) 고정 (hits 비어도 유지)
    - Step2: 정렬 규칙 추가 (rank/score → evidence_level → year)
    - Step3: Top-K 제한 (기본 10)
    - Step4: user_context는 '요구 조건'으로만 Target Profile에 기록 (새 사실 생성 금지)
    """

    # hits 비어도 섹션 키 고정
    if not hits:
        lines = [
            f"- Query: {user_query}",
            "- Coverage: papers=0, claims=0, years=None~None",
            f"- Notes: {'(user_context provided)' if user_context else '(none)'}",
        ]
        if user_context:
            # Step4: user_context는 요구조건으로만 반영 (길이 제한)
            lines.append(f"- User constraints: {user_context[:200]}")

        target_profile = DossierSection(text="\n".join(lines), citations=[])

        empty = DossierSection(text="(none)", citations=[])

        return TargetDossier(
            dossier_id="temp",
            target=user_query,
            sections={
                "target_profile": [target_profile],
                "key_claims": [],
                "evidence_level_summary": [empty],
                "risk_signals": [],
                "next_validation_steps": [DossierSection(
                    text="- (No suggested steps based on evidence gaps)",
                    citations=[]
                )],
            },
            format="markdown",
        )

    # 정렬 적용
    hits_sorted = sorted(hits, key=lambda h: (_rank_key(h), _evidence_key(h), _year_key(h)))

    # Top-K 적용 (Key Claims에만 적용)
    hits_for_claims = hits_sorted[:MAX_CLAIMS]

    # --- coverage 요약 ---
    papers = sorted({h.paper.pmid for h in hits_sorted if h.paper and h.paper.pmid})
    years = [h.paper.year for h in hits_sorted if h.paper and h.paper.year is not None]
    year_min = min(years) if years else None
    year_max = max(years) if years else None

    # --- evidence level summary ---
    ev = defaultdict(list)
    for h in hits_sorted:
        ev[h.evidence_level].append(h.claim_id)

    # 고정 섹션: Target Profile
    profile_lines = [
        f"- Query: {user_query}",
        f"- Coverage: papers={len(papers)}, claims={len(hits_sorted)}, years={year_min}~{year_max}",
        f"- Notes: {'(user_context provided)' if user_context else '(none)'}",
    ]
    if user_context:
        # Step4: user_context는 요구조건으로만 반영
        profile_lines.append(f"- User constraints: {user_context[:200]}")

    target_profile_section = DossierSection(text="\n".join(profile_lines), citations=papers[:])

    # 고정 섹션: Key Claims (각 claim = 섹션 1개)
    key_claim_sections: List[DossierSection] = []
    for h in hits_for_claims:
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

    # 고정 섹션: Evidence Level Summary
    ev_text = "\n".join([
        f"- in_vitro: {len(ev.get('in_vitro', []))} claim(s) -> {ev.get('in_vitro', [])}",
        f"- in_vivo: {len(ev.get('in_vivo', []))} claim(s) -> {ev.get('in_vivo', [])}",
        f"- clinical: {len(ev.get('clinical', []))} claim(s) -> {ev.get('clinical', [])}",
    ])
    evidence_level_section = DossierSection(text=ev_text, citations=papers[:])

    # 고정 섹션: Risk Signals (있는 것만)
    risk_sections: List[DossierSection] = []
    for h in hits_sorted:
        if not h.risk_signals:
            continue
        risk_text = "\n".join([
            f"### Risks for Claim {h.claim_id}",
            _fmt_risk_lines(h),
        ])
        pmids = sorted(_collect_pmids_from_hit(h))
        risk_sections.append(DossierSection(text=risk_text, citations=pmids))

    # 고정 섹션: Next Validation Steps (gap 기반)
    next_steps_lines: List[str] = []
    if len(ev.get("clinical", [])) == 0:
        next_steps_lines.append(
            "- Step: 임상(Clinical) 근거가 부족 → 임상 단계 데이터/연구 설계 검토 필요 (gap:clinical_empty)"
        )
    if len(ev.get("in_vivo", [])) == 0:
        next_steps_lines.append(
            "- Step: 동물(In vivo) 근거가 부족 → in vivo 단계 검증 필요 (gap:in_vivo_empty)"
        )
    if not next_steps_lines:
        next_steps_lines.append("- (No suggested steps based on evidence gaps)")

    next_steps_section = DossierSection(text="\n".join(next_steps_lines), citations=papers[:])

    # 섹션 키 고정 (항상 동일 키)
    sections: Dict[str, List[DossierSection]] = {
        "target_profile": [target_profile_section],
        "key_claims": key_claim_sections,
        "evidence_level_summary": [evidence_level_section],
        "risk_signals": risk_sections,
        "next_validation_steps": [next_steps_section],
    }

    return TargetDossier(
        dossier_id="temp",   # 실제 id는 orchestrator/서비스에서 주입 가능
        target=user_query,
        sections=sections,
        format="markdown",
    )
