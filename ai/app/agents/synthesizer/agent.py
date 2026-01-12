from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime


class SynthesizerAgent:
    """
    ✅ 출력은 무조건 팀 스키마 TargetDossier(dict)만 반환한다.
    - 개발 편의(markdown 렌더링)는 to_markdown()으로만 제공하고, run() 반환에는 포함하지 않는다.
    """

    def _new_dossier_id(self) -> str:
        return datetime.now().strftime("d_%Y%m%d_%H%M%S")

    def _as_list(self, v: Any) -> List[Any]:
        return v if isinstance(v, list) else []

    # ----------------------------
    # 1) 팀 ValidatedClaims 입력 처리
    # ----------------------------
    def _build_sections_from_validated_claims(self, validated: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        claims = self._as_list(validated.get("claims"))
        if not claims:
            return {
                "summary": [{
                    "text": "Validator 결과(claims)가 비어 있습니다.",
                    "citations": [],
                }]
            }

        key_claim_lines: List[str] = []
        risk_lines: List[str] = []
        next_lines: List[str] = []

        all_pmids_for_key: List[str] = []
        all_pmids_for_risk: List[str] = []

        for idx, c in enumerate(claims, 1):
            norm = c.get("normalized_claim") or c.get("claim") or "-"
            consistency = c.get("consistency") or "-"
            ev_items = self._as_list(c.get("evidence"))
            ev_summary = c.get("evidence_summary") or {}

            key_claim_lines.append(f"### Claim {idx}")
            key_claim_lines.append(f"- 주장: {norm}")
            key_claim_lines.append(f"- 일관성(consistency): {consistency}")

            if isinstance(ev_summary, dict) and ev_summary:
                key_claim_lines.append(
                    f"- 근거 분포: in_vitro={ev_summary.get('in_vitro', 0)}, "
                    f"in_vivo={ev_summary.get('in_vivo', 0)}, clinical={ev_summary.get('clinical', 0)}"
                )

            if ev_items:
                key_claim_lines.append("- 근거(evidence):")
                for e in ev_items[:6]:
                    pmid = (e.get("pmid") or "").strip()
                    sid = (e.get("sentence_id") or "").strip()
                    lvl = (e.get("experiment_level") or "").strip()
                    key_claim_lines.append(f"  - PMID {pmid or '-'} | sentence_id={sid or '-'} | level={lvl or '-'}")
                    if pmid:
                        all_pmids_for_key.append(pmid)
            else:
                key_claim_lines.append("- 근거(evidence): (없음)")

            key_claim_lines.append("")

            rs = self._as_list(c.get("risk_signals"))
            for r in rs[:6]:
                rtype = (r.get("type") or "-").strip()
                pmid = (r.get("pmid") or "").strip()
                sid = (r.get("sentence_id") or "").strip()
                risk_lines.append(f"- [{rtype}] PMID {pmid or '-'} | sentence_id={sid or '-'}")
                if pmid:
                    all_pmids_for_risk.append(pmid)

        next_lines.append("- (다음 단계는 Validator/중앙 에이전트 정책에 따라 결정)")

        return {
            "key_claims": [{
                "text": "\n".join(key_claim_lines).strip() or "(없음)",
                "citations": sorted(list(set(all_pmids_for_key))),
            }],
            "risk_signals": [{
                "text": "\n".join(risk_lines).strip() if risk_lines else "(특이 위험 신호 없음 / 또는 미탐지)",
                "citations": sorted(list(set(all_pmids_for_risk))),
            }],
            "next_steps": [{
                "text": "\n".join(next_lines).strip(),
                "citations": [],
            }],
        }

    # ----------------------------
    # 2) 구버전(임시 JSON) 입력 처리
    # ----------------------------
    def _build_sections_from_legacy(self, validated: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        profile = validated.get("target_profile") or {}
        key_claims = self._as_list(validated.get("key_claims"))
        risks = self._as_list(validated.get("risk_signals"))
        next_steps = self._as_list(validated.get("next_validation_steps"))
        options = self._as_list(validated.get("options"))

        summary_lines = [
            f"- Target: {profile.get('target', '-')}",
            f"- Disease/Context: {profile.get('disease', '-')}",
            f"- Scope: {profile.get('scope_note', '-')}",
        ]

        key_lines: List[str] = []
        key_pmids: List[str] = []

        for i, kc in enumerate(key_claims, 1):
            key_lines.append(f"### Claim {i}")
            key_lines.append(f"- 주장: {kc.get('claim','-')}")
            ev_levels = kc.get("evidence_level") or []
            key_lines.append(f"- Evidence Level: {', '.join(ev_levels) if ev_levels else '-'}")

            evidences = self._as_list(kc.get("evidences"))
            if evidences:
                key_lines.append("- 근거(evidences):")
                for ev in evidences[:6]:
                    pmid = (ev.get("pmid") or "").strip()
                    sent = (ev.get("sentence") or "").strip()
                    url = (ev.get("url") or "").strip()
                    key_lines.append(f"  - PMID {pmid or '-'} | {sent or '(no sentence)'} | {url or '(no link)'}")
                    if pmid:
                        key_pmids.append(pmid)
            else:
                key_lines.append("- 근거(evidences): (없음)")
            key_lines.append("")

        risk_lines: List[str] = []
        risk_pmids: List[str] = []
        for i, r in enumerate(risks, 1):
            risk_lines.append(f"### Risk {i}")
            risk_lines.append(f"- 신호: {r.get('signal','-')}")
            evidences = self._as_list(r.get("evidences"))
            for ev in evidences[:6]:
                pmid = (ev.get("pmid") or "").strip()
                sent = (ev.get("sentence") or "").strip()
                url = (ev.get("url") or "").strip()
                risk_lines.append(f"  - 근거: PMID {pmid or '-'} | {sent or '(no sentence)'} | {url or '(no link)'}")
                if pmid:
                    risk_pmids.append(pmid)
            risk_lines.append("")

        next_lines = [f"- {s}" for s in next_steps] if next_steps else ["- (제안 없음)"]

        opt_lines: List[str] = []
        if options:
            for op in options:
                opt_lines.append(f"- {op.get('path','-')}: {op.get('rationale','-')}")
        else:
            opt_lines.append("- (선택지 없음)")

        return {
            "summary": [{
                "text": "\n".join(summary_lines),
                "citations": [],
            }],
            "key_claims": [{
                "text": "\n".join(key_lines).strip() or "(없음)",
                "citations": sorted(list(set(key_pmids))),
            }],
            "risk_signals": [{
                "text": "\n".join(risk_lines).strip() if risk_lines else "(특이 위험 신호 없음 / 또는 미탐지)",
                "citations": sorted(list(set(risk_pmids))),
            }],
            "next_steps": [{
                "text": "\n".join(next_lines),
                "citations": [],
            }],
            "options": [{
                "text": "\n".join(opt_lines),
                "citations": [],
            }],
        }

    def to_target_dossier(self, validated: Dict[str, Any]) -> Dict[str, Any]:
        target = (
            (validated.get("target") or "").strip()
            or ((validated.get("target_profile") or {}).get("target") or "").strip()
            or "Unknown Target"
        )

        dossier_id = (validated.get("dossier_id") or "").strip() or self._new_dossier_id()

        if isinstance(validated.get("claims"), list):
            sections = self._build_sections_from_validated_claims(validated)
        else:
            sections = self._build_sections_from_legacy(validated)

        # ✅ team dossier.py 스키마 "정확히" 맞춘 반환
        return {
            "dossier_id": dossier_id,
            "target": target,
            "sections": sections,
            "format": "markdown",
        }

    def to_markdown(self, target_dossier: Dict[str, Any]) -> str:
        target = target_dossier.get("target", "Unknown Target")
        dossier_id = target_dossier.get("dossier_id", "-")
        sections = target_dossier.get("sections") or {}

        md: List[str] = []
        md.append(f"# Target Dossier: {target}")
        md.append(f"- dossier_id: `{dossier_id}`")
        md.append("")

        for sec_name, sec_list in sections.items():
            md.append(f"## {sec_name}")
            if not isinstance(sec_list, list) or not sec_list:
                md.append("- (empty)")
                md.append("")
                continue

            for block in sec_list:
                text = (block.get("text") or "").strip()
                citations = block.get("citations") or []
                if text:
                    md.append(text)
                if citations:
                    md.append("")
                    md.append(f"- citations(PMID): {', '.join(citations)}")
                md.append("")

        return "\n".join(md).strip() + "\n"

    def run(self, validated: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ 스키마 엄격 대응:
        - run()은 TargetDossier(dict)만 반환한다.
        """
        return self.to_target_dossier(validated)
