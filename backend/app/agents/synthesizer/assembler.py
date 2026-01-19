# app/agents/synthesizer/assembler.py
from typing import List, Dict, Set, Any, Tuple
from collections import defaultdict

from app.schemas.vector_hit import VectorHit
from app.schemas.dossier import TargetDossier, DossierSection

# 근거 수준 우선순위 정의
EVIDENCE_PRIORITY = {"clinical": 0, "in_vivo": 1, "in_vitro": 2}
MAX_CLAIMS = 10

# 보고서 맨 위 경고 문구(고정)
DISCLAIMER = "⚠️ 이 보고서는 제공된 근거(quote/PMID/URL)에 기반한 정리이며, 최종 판단과 책임은 사용자에게 있습니다."


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _collect_pmids(hit: VectorHit) -> Set[str]:
    
    pmids: Set[str] = set()

    if hit.paper and getattr(hit.paper, "pmid", None):
        pmids.add(hit.paper.pmid)

    for c in (hit.evidence or []):
        if getattr(c, "pmid", None):
            pmids.add(c.pmid)

    for r in (hit.risk_signals or []):
        cit = getattr(r, "citation", None)
        if cit and getattr(cit, "pmid", None):
            pmids.add(cit.pmid)

    return pmids


def _fmt_evidence_lines(hit: VectorHit) -> str:
    """
    근거 표시 강화(해석/변형 금지):
    - Evidence 전체를 Quote + PMID + URL로 출력
    """
    lines: List[str] = []
    for c in (hit.evidence or []):
        quote = getattr(c, "quote", "") or ""
        pmid = getattr(c, "pmid", "") or ""
        url = getattr(c, "url", "") or ""
        lines.append(f'- Quote: "{quote}"')
        lines.append(f"  Source: PMID: {pmid} | {url}")
    return "\n".join(lines) if lines else "- (No evidence provided)"


def _fmt_risk_lines(hit: VectorHit) -> str:
    """
    Risk는 근거 있을 때만, quote/PMID/URL 그대로 표시
    """
    if not (hit.risk_signals or []):
        return "- (No risk signals)"

    lines: List[str] = []
    for r in hit.risk_signals:
        r_type = getattr(r, "type", "") or ""
        cit = getattr(r, "citation", None)

        quote = getattr(cit, "quote", "") if cit else ""
        pmid = getattr(cit, "pmid", "") if cit else ""
        url = getattr(cit, "url", "") if cit else ""

        lines.append(f"- Risk: {r_type}")
        lines.append(f'  Evidence: "{quote}"')
        lines.append(f"  Source: PMID: {pmid} | {url}")
    return "\n".join(lines)


def _tokenize(text: str) -> Set[str]:
    """
    텍스트 기반(관찰)용 토큰화
    - 의미 해석/추론이 아니라 '겹침' 관찰만
    """
    if not text:
        return set()
    raw = (
        text.replace("\n", " ")
        .replace("\t", " ")
        .replace(",", " ")
        .replace(".", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace("[", " ")
        .replace("]", " ")
        .replace("/", " ")
        .replace(":", " ")
        .replace(";", " ")
        .replace("|", " ")
        .lower()
        .split()
    )
    return {t.strip() for t in raw if len(t.strip()) >= 3}


def _calc_intent_overlap(user_query: str, user_context: str, hits: List[VectorHit]) -> Tuple[int, List[str], List[str]]:
    """
    사용자 의도(user_query/user_context) vs claim_text의 텍스트 겹침 관찰
    반환:
    - max_overlap: 최대 겹침 수
    - top_claim_ids: 겹침이 있었던 상위 claim_id 몇 개
    - support_pmids: 그 claim들에서 수집된 pmid
    """
    intent_tokens = _tokenize(user_query) | _tokenize(user_context)
    if not intent_tokens:
        return 0, [], []

    scored: List[Tuple[int, VectorHit]] = []
    for h in hits:
        ct = _tokenize(getattr(h, "claim_text", "") or "")
        overlap = len(intent_tokens & ct)
        scored.append((overlap, h))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [(s, h) for (s, h) in scored if s > 0][:3]

    if not top:
        return 0, [], []

    pmids: Set[str] = set()
    claim_ids: List[str] = []
    max_overlap = top[0][0]

    for s, h in top:
        claim_ids.append(str(getattr(h, "claim_id", "")))
        pmids |= _collect_pmids(h)

    return max_overlap, claim_ids, sorted(pmids)


def _rubric_assess(ev_map: Dict[str, List[str]], hits: List[VectorHit], user_query: str, user_context: str) -> Tuple[str, int, List[str], List[str]]:
    """
    '가치판단'을 임의로 하지 않고, 규칙 기반(Rubric)으로 제한
    출력:
    - confidence_label: High / Moderate / Exploratory
    - score: 계산된 점수
    - reasons: 왜 그렇게 나왔는지(설명 가능)
    - supports: 지원 PMID (hit들에서만 수집)
    """
    clinical_n = len(ev_map.get("clinical", []))
    in_vivo_n = len(ev_map.get("in_vivo", []))
    in_vitro_n = len(ev_map.get("in_vitro", []))

    has_risk = any((h.risk_signals or []) for h in hits)

    years = [getattr(getattr(h, "paper", None), "year", None) for h in hits]
    years = [y for y in years if y is not None]
    year_max = max(years) if years else None

    overlap, overlap_claims, overlap_pmids = _calc_intent_overlap(user_query, user_context, hits)

    # --- Rubric scoring ---
    score = 0
    reasons: List[str] = []

    # Evidence level
    if clinical_n > 0:
        score += 3
        reasons.append(f"+3 clinical evidence present (clinical={clinical_n})")
    if in_vivo_n > 0:
        score += 2
        reasons.append(f"+2 in_vivo evidence present (in_vivo={in_vivo_n})")
    if (clinical_n == 0 and in_vivo_n == 0 and in_vitro_n > 0):
        score += 1
        reasons.append(f"+1 only in_vitro evidence present (in_vitro={in_vitro_n})")

    # Risk penalty
    if has_risk:
        score -= 2
        reasons.append("-2 risk_signals present")

    # Recency bonus (메타)
    if year_max is not None:

        if _safe_int(year_max, 0) >= 2021:
            score += 1
            reasons.append(f"+1 recency bonus (max_year={year_max})")

    if overlap > 0:
        score += 1
        reasons.append(f"+1 intent overlap observed (top_claims={overlap_claims})")

    # --- Confidence mapping ---
    # High: score >= 4 and clinical present and not risk-heavy(여기선 risk 있으면 페널티 이미 반영)
    # Moderate: score 2~3
    # Exploratory: score <= 1
    if score >= 4 and clinical_n > 0:
        confidence = "High"
    elif score >= 2:
        confidence = "Moderate"
    else:
        confidence = "Exploratory"

    # supports = 전체 pmid + overlap 관련 pmid
    all_pmids: Set[str] = set()
    for h in hits:
        all_pmids |= _collect_pmids(h)
    supports = sorted(all_pmids | set(overlap_pmids))

    return confidence, score, reasons, supports


def _build_additional_retrieval_suggestions(user_query: str, user_context: str, ev_map: Dict[str, List[str]]) -> List[str]:
    """
    '논문 찾아줘'를 Synthesizer가 직접 수행하지 않고,
    Retriever/Orchestrator가 재호출할 수 있게 '쿼리 제안'만 출력.
    """
    tokens = sorted(list(_tokenize(user_query) | _tokenize(user_context)))
    seed = " ".join(tokens[:8]) if tokens else user_query

    suggestions: List[str] = []
    suggestions.append("## Additional literature suggestions (queries)")
    suggestions.append("- 아래는 추가 근거(특히 공백 레벨)를 메우기 위한 '검색 제안'이며, 실제 검색은 Retriever/Orchestrator가 수행합니다.")

    # gap 기반 쿼리 제안
    if len(ev_map.get("clinical", [])) == 0:
        suggestions.append(f'- Query: "{seed} clinical trial OR cohort OR real-world" (goal: fill gap:clinical_empty)')
    if len(ev_map.get("in_vivo", [])) == 0:
        suggestions.append(f'- Query: "{seed} in vivo OR mouse OR animal model" (goal: fill gap:in_vivo_empty)')
    if len(ev_map.get("in_vitro", [])) == 0:
        suggestions.append(f'- Query: "{seed} in vitro OR cell line OR assay" (goal: fill gap:in_vitro_empty)')

    # 일반 확장(과장 금지, 탐색 범위 확장)
    suggestions.append(f'- Query: "{seed} mechanism OR pathway OR biomarker" (goal: broaden mechanistic context)')
    suggestions.append(f'- Query: "{seed} safety OR adverse events OR toxicity" (goal: check risk signals)')

    return suggestions


def _build_conclusion_and_direction(
    user_query: str,
    user_context: str,
    hits_sorted: List[VectorHit],
    ev_map: Dict[str, List[str]],
) -> Tuple[str, List[str]]:
    """
    결론/방향성 블록:
    - '임의 판단'이 아니라 rubric 결과 + 근거 PMID로 구속
    - 표현 수위는 Confidence에 따라 제한
    - 섹션 키 추가 없이 text 블록으로만 제공
    """
    confidence, score, reasons, supports = _rubric_assess(ev_map, hits_sorted, user_query, user_context)

    # 결론 문장 수위 제한(중요)
    if confidence == "High":
        conclusion_line = (
            "- Conclusion: 제공된 근거 분포(특히 clinical 포함)와 사용자 의도-claim 텍스트 겹침 관찰을 종합할 때, "
            "사용자의 연구 방향은 근거에 의해 강하게 지지되는 편입니다."
        )
    elif confidence == "Moderate":
        conclusion_line = (
            "- Conclusion: 제공된 근거 분포(in vivo/일부 임상 여부 등)와 사용자 의도-claim 텍스트 겹침 관찰을 종합할 때, "
            "사용자의 연구 방향은 유의미하게 시사됩니다(추가 검증 필요)."
        )
    else:
        conclusion_line = (
            "- Conclusion: 현재 근거는 탐색적(Exploratory) 단계로 보이며, 사용자 연구 방향은 가설/탐색 가치 중심으로 평가됩니다."
        )

    # 방향성(로드맵) = gap/risk 기반 제안 수준
    direction_lines: List[str] = []
    direction_lines.append("## Research direction (bounded, evidence-gap anchored)")
    if len(ev_map.get("clinical", [])) == 0:
        direction_lines.append("- Direction: 임상 근거 공백(gap:clinical_empty)을 메우기 위해 임상 연구/코호트/리얼월드 근거를 우선 탐색하는 것이 타당합니다(제안 수준).")
    if len(ev_map.get("in_vivo", [])) == 0:
        direction_lines.append("- Direction: in vivo 근거 공백(gap:in_vivo_empty)을 메우기 위해 동물 모델 기반 검증 또는 재현성 확인이 필요합니다(제안 수준).")
    if any((h.risk_signals or []) for h in hits_sorted):
        direction_lines.append("- Direction: risk_signals가 관찰되므로 안전성/한계 조건을 함께 점검하는 보완 탐색이 필요합니다(제안 수준).")
    if not direction_lines or len(direction_lines) == 1:
        direction_lines.append("- Direction: 현재 evidence 분포상 주요 단계 공백이 뚜렷하지 않으며, 재현성/확장성 관점의 추가 검증을 고려할 수 있습니다(제안 수준).")

    lines: List[str] = []
    lines.append("## Conclusion (Rubric-based, evidence-anchored)")
    lines.append(conclusion_line)
    lines.append(f"- Confidence: {confidence} (rubric_score={score})")
    lines.append("- Why (rubric reasons):")
    for r in reasons:
        lines.append(f"  - {r}")
    lines.append(f"- Supports: PMID {', '.join(supports) if supports else '(none)'}")

    if user_context:
        lines.append(f"- User intent (from user_context): {user_context[:200]}")

    # “종합”은 해석이 아니라, 대표 claim + evidence를 붙여 사용자 검증 가능하게 제공
    lines.append("- Consolidated evidence view (top claims, no paraphrase):")
    for h in hits_sorted[: min(5, MAX_CLAIMS)]:
        lines.append(f"### Claim {getattr(h, 'claim_id', '')}")
        lines.append(f"- Claim: {getattr(h, 'claim_text', '')}")
        lines.append(f"- Evidence level: {getattr(h, 'evidence_level', '')}")
        lines.append("- Evidence:")
        lines.append(_fmt_evidence_lines(h))

    # 추가 검색 제안(실행은 Retriever/Orchestrator)
    lines.extend(_build_additional_retrieval_suggestions(user_query, user_context, ev_map))
    lines.extend(direction_lines)

    return "\n".join(lines), supports


def build_dossier_sections(user_query: str, hits: List[VectorHit], user_context: str = "") -> TargetDossier:
    
    # 데이터 정렬 및 섹션 조립 로직을 수행합니다.

    print(f"[Assembler] Processing {len(hits)} knowledge chunks...")

    # hits 비어도 섹션 키 고정
    if not hits:
        profile_text = "\n".join([
            DISCLAIMER,
            f"- 질의어: {user_query}",
            "- 분석 논문 수: 0건",
            "- 추출된 주장 수: 0건",
            f"- User constraints: {user_context[:200]}" if user_context else "- User constraints: (none)",
            "- (No evidence provided; conclusion omitted)",
        ])
        sections = {
            "target_profile": [DossierSection(text=profile_text, citations=[])],
            "key_claims": [],
            "evidence_level_summary": [DossierSection(text="(none)", citations=[])],
            "risk_signals": [],
            "next_validation_steps": [DossierSection(
                text="- (No suggested steps based on evidence gaps)",
                citations=[]
            )],
        }
        return TargetDossier(dossier_id="doc_01", target=user_query, sections=sections, format="markdown")

    # 1. 정렬: 검색 순위 -> 근거 수준 -> 발행 연도
    hits_sorted = sorted(hits, key=lambda h: (
        h.retrieval.get("rank", 999) if h.retrieval else 999,
        EVIDENCE_PRIORITY.get(getattr(h, "evidence_level", None), 99),
        -(getattr(getattr(h, "paper", None), "year", 0) or 0)
    ))

    # 2. 섹션 데이터 구성
    sections: Dict[str, List[DossierSection]] = {}
    ev_map: Dict[str, List[str]] = defaultdict(list)
    for h in hits_sorted:
        ev_map[getattr(h, "evidence_level", "(unknown)")].append(getattr(h, "claim_id", ""))

    # [Target Profile] (맨 위 경고 문구 추가)
    papers = sorted({h.paper.pmid for h in hits_sorted if h.paper and getattr(h.paper, "pmid", None)})
    profile_lines = [
        DISCLAIMER,
        f"- 질의어: {user_query}",
        f"- 분석 논문 수: {len(papers)}건",
        f"- 추출된 주장 수: {len(hits_sorted)}건",
        f"- User constraints: {user_context[:200]}" if user_context else "- User constraints: (none)",
    ]
    sections["target_profile"] = [DossierSection(text="\n".join(profile_lines), citations=papers)]

    # [Key Claims] (각 claim마다 Evidence(quote+PMID+URL) 포함)
    sections["key_claims"] = [
        DossierSection(
            text="\n".join([
                f"### [주장 {getattr(h, 'claim_id', '')}]",
                f"- 내용: {getattr(h, 'claim_text', '')}",
                f"- 근거 수준: {getattr(h, 'evidence_level', '')}",
                "- Evidence:",
                _fmt_evidence_lines(h),
            ]),
            citations=sorted(_collect_pmids(h))
        ) for h in hits_sorted[:MAX_CLAIMS]
    ]

    # [Evidence Summary] (분포 + claim_id 목록)
    ev_summary = "\n".join([
        f"- in_vitro: {len(ev_map.get('in_vitro', []))}건 -> {ev_map.get('in_vitro', [])}",
        f"- in_vivo: {len(ev_map.get('in_vivo', []))}건 -> {ev_map.get('in_vivo', [])}",
        f"- clinical: {len(ev_map.get('clinical', []))}건 -> {ev_map.get('clinical', [])}",
    ])
    sections["evidence_level_summary"] = [DossierSection(text=ev_summary, citations=papers)]

    # [Risk Signals] (근거 있을 때만)
    risks: List[DossierSection] = []
    for h in hits_sorted:
        if not (h.risk_signals or []):
            continue
        risks.append(DossierSection(
            text="\n".join([
                f"### [주장 {getattr(h, 'claim_id', '')}] Risk Signals",
                _fmt_risk_lines(h),
            ]),
            citations=sorted(_collect_pmids(h))
        ))
    sections["risk_signals"] = risks

    # [Next Validation Steps] (Gap 분석) + 결론/방향/추가검색 제안 블록을 '같은 섹션 텍스트'로 덧붙임
    steps: List[str] = []
    if len(ev_map.get("clinical", [])) == 0:
        steps.append("- 임상(Clinical) 데이터 공백(gap:clinical_empty): 추가 임상 문헌 검토/설계 검토 필요(제안 수준, 결론 아님).")
    if len(ev_map.get("in_vivo", [])) == 0:
        steps.append("- 동물 실험(In vivo) 데이터 공백(gap:in_vivo_empty): 생체 내 검증 근거 보완 필요(제안 수준, 결론 아님).")
    if not steps:
        steps.append("- (No suggested steps based on evidence gaps)")

    base_steps_text = "\n".join(steps)

    #  결론 + 방향성 + 추가검색 제안 (rubric 기반, 근거 PMID로 구속)
    conclusion_text, conclusion_supports = _build_conclusion_and_direction(
        user_query=user_query,
        user_context=user_context,
        hits_sorted=hits_sorted,
        ev_map=ev_map,
    )

    final_text = "\n\n".join([base_steps_text, conclusion_text])
    final_citations = sorted(set(papers) | set(conclusion_supports))

    sections["next_validation_steps"] = [DossierSection(text=final_text, citations=final_citations)]

    #  스키마 구조 엄수
    return TargetDossier(dossier_id="doc_01", target=user_query, sections=sections, format="markdown")
