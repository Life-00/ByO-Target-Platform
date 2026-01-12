from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime

# typing, datetime 는 파이썬 표준 라이브러리(내장)


class SynthesizerAgent:
    """
    최종 산출물(TargetDossier)을 생성하는 Synthesizer.

    - 입력은 2가지 모두 지원(하위호환):
      1) (구버전/임시) {
           "target_profile": {...},
           "key_claims": [...],
           "risk_signals": [...],
           "next_validation_steps": [...],
           "options": [...]
         }
      2) (팀 스키마 기반) {
           "claims": [  # ValidatedClaims
             {
               "claim_id": "...",
               "normalized_claim": "...",
               "evidence": [{"pmid":"...", "sentence_id":"...", "experiment_level":"..."}],
               "evidence_summary": {"in_vitro":3, "in_vivo":1, "clinical":0},
               "consistency": "consistent|conflicting|insufficient",
               "risk_signals": [{"type":"toxicity|failure|inconsistency","pmid":"...","sentence_id":"..."}]
             }, ...
           ],
           # (선택) target, dossier_id 등 메타가 상위에서 추가될 수 있음
         }

    - 출력(팀 dossier.py TargetDossier 형태):
      {
        "dossier_id": str,
        "target": str,
        "sections": Dict[str, List[{"text": str, "citations": List[str]}]],
        "format": "markdown"
      }
    """

    def _new_dossier_id(self) -> str:
        # timestamp 기반 간단 ID (추후 팀 규칙이 있으면 바꾸면 됨)
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

        # Claim 섹션 구성
        for idx, c in enumerate(claims, 1):
            norm = c.get("normalized_claim") or c.get("claim") or "-"
            consistency = c.get("consistency") or "-"
            ev_items = self._as_list(c.get("evidence"))
            ev_summary = c.get("evidence_summary") or {}

            key_claim_lines.append(f"### Claim {idx}")
            key_claim_lines.append(f"- 주장: {norm}")
            key_claim_lines.append(f"- 일관성(consistency): {consistency}")

            # evidence summary(있으면 표시)
            if isinstance(ev_summary, dict) and ev_summary:
                # 팀 캡쳐 주석은 {'in_vitro':3,'in_vivo':1,'clinical':0} 형태
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

            # risk_signals(Claim 내부에 들어있음)
            rs = self._as_list(c.get("risk_signals"))
            for r in rs[:6]:
                rtype = (r.get("type") or "-").strip()
                pmid = (r.get("pmid") or "").strip()
                sid = (r.get("sentence_id") or "").strip()
                risk_lines.append(f"- [{rtype}] PMID {pmid or '-'} | sentence_id={sid or '-'}")
                if pmid:
                    all_pmids_for_risk.append(pmid)

        # Next steps는 Validator가 별도로 주지 않을 수도 있어서 기본 안내만
        next_lines.append("- (다음 단계는 Validator/중앙 에이전트 정책에 따라 결정)")

        # 섹션 dict[str, list[DossierSection]] 형태로 반환
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
        """
        ✅ 팀 dossier.py(TargetDossier) 스키마 형태로 dict 생성
        """
        # target 이름 추출: 팀쪽 입력에는 target이 따로 없을 수 있으니 최대한 찾아봄
        target = (
            (validated.get("target") or "").strip()
            or ((validated.get("target_profile") or {}).get("target") or "").strip()
            or "Unknown Target"
        )

        dossier_id = (validated.get("dossier_id") or "").strip() or self._new_dossier_id()

        # 팀 ValidatedClaims 형태면 "claims"가 리스트로 존재
        if isinstance(validated.get("claims"), list):
            sections = self._build_sections_from_validated_claims(validated)
        else:
            sections = self._build_sections_from_legacy(validated)

        return {
            "dossier_id": dossier_id,
            "target": target,
            "sections": sections,
            "format": "markdown",
        }

    def to_markdown(self, target_dossier: Dict[str, Any]) -> str:
        """
        ✅ TargetDossier(sections 기반) -> 사람이 읽기 좋은 마크다운으로 렌더링(개발 편의)
        """
        target = target_dossier.get("target", "Unknown Target")
        dossier_id = target_dossier.get("dossier_id", "-")
        sections = target_dossier.get("sections") or {}

        md: List[str] = []
        md.append(f"# Target Dossier: {target}")
        md.append(f"- dossier_id: `{dossier_id}`")
        md.append("")

        # sections는 Dict[str, List[DossierSection]]
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
        ✅ 최종 반환: 팀 스키마 TargetDossier dict + (추가) dossier_markdown
        """
        dossier_obj = self.to_target_dossier(validated)
        dossier_md = self.to_markdown(dossier_obj)
        return {
            "format": "markdown",
            "dossier": dossier_obj,          # 팀 스키마에 맞는 구조(dict)
            "dossier_markdown": dossier_md,  # 사람이 보기 좋게 렌더링한 문자열(선택)
        }
