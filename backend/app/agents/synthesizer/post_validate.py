# app/agents/synthesizer/post_validate.py
from __future__ import annotations

from typing import List

from app.schemas.dossier import TargetDossier, DossierSection
from .report_policy import DEFAULT_POLICY, ReportPolicy


class PostValidateError(ValueError):
    pass


def _has_all_markers(text: str, markers: List[str]) -> bool:
    if not text:
        return False
    return all(m in text for m in markers)


def _is_cannot_say_report(dossier: TargetDossier) -> bool:
    tp = dossier.sections.get("target_profile", [])
    if not tp:
        return False
    head = (tp[0].text or "")
    return "분석 논문 수: 0건" in head and "추출된 주장 수: 0건" in head


def _validate_required_sections(dossier: TargetDossier, policy: ReportPolicy) -> None:
    missing = [k for k in policy.required_section_keys if k not in dossier.sections]
    if missing:
        raise PostValidateError(f"Missing required section keys: {missing}")


def _extract_pmid_url_from_text(text: str) -> List[tuple[str, str]]:
    """
    assembler가 찍는 포맷:
      Source: PMID: {pmid} | {url}
    을 파싱해서 (pmid, url) 리스트로 반환
    """
    pairs: List[tuple[str, str]] = []
    for line in (text or "").splitlines():
        if "Source: PMID:" not in line:
            continue
        # 예: "  Source: PMID: 123456 | https://..."
        after = line.split("Source: PMID:", 1)[-1].strip()
        if "|" in after:
            pmid_part, url_part = after.split("|", 1)
            pmid = pmid_part.strip()
            url = url_part.strip()
        else:
            pmid = after.strip()
            url = ""
        pairs.append((pmid, url))
    return pairs


def _validate_key_claims(dossier: TargetDossier, policy: ReportPolicy) -> None:
    key_claims: List[DossierSection] = dossier.sections.get("key_claims", [])

    if not key_claims and _is_cannot_say_report(dossier):
        return

    if not key_claims:
        raise PostValidateError("key_claims is empty for a non-empty report.")

    for idx, sec in enumerate(key_claims):
        txt = (sec.text or "").strip()
        if not txt:
            raise PostValidateError(f"key_claims[{idx}] text is empty.")

        # 1) Evidence 마커 강제
        if not _has_all_markers(txt, list(policy.required_evidence_markers)):
            raise PostValidateError(
                f"key_claims[{idx}] missing required evidence markers. "
                f"required={list(policy.required_evidence_markers)}"
            )

        # 2) (강화) "No evidence provided" 같은 탈출구 문구는 hits>0에서 금지
        if "No evidence provided" in txt:
            raise PostValidateError(f"key_claims[{idx}] contains 'No evidence provided' (not allowed).")

        # 3) (강화) Quote 빈 문자열 방지: '- Quote: ""' 패턴 방지
        if '- Quote: ""' in txt or '- Quote: "' in txt and '""' in txt:
            # 완전 정확 파싱까지는 아니고, 빈 quote 흔한 패턴만 1차 차단
            if '- Quote: ""' in txt:
                raise PostValidateError(f"key_claims[{idx}] has empty quote.")

        # 4) (강화) Source 라인에서 pmid/url 비어 있으면 실패
        pairs = _extract_pmid_url_from_text(txt)
        if not pairs:
            raise PostValidateError(f"key_claims[{idx}] has no parsable Source line.")
        for pmid, url in pairs:
            if not pmid:
                raise PostValidateError(f"key_claims[{idx}] has empty PMID in Source line.")
            if not url:
                raise PostValidateError(f"key_claims[{idx}] has empty URL in Source line.")

        # 5) citations 최소 1개
        if not isinstance(sec.citations, list) or len(sec.citations) == 0:
            raise PostValidateError(f"key_claims[{idx}] citations empty.")


def _validate_next_steps(dossier: TargetDossier) -> None:
    nvs: List[DossierSection] = dossier.sections.get("next_validation_steps", [])
    if not nvs:
        raise PostValidateError("next_validation_steps missing or empty.")
    if not (nvs[0].text or "").strip():
        raise PostValidateError("next_validation_steps[0] text is empty.")


def post_validate_dossier(dossier: TargetDossier, policy: ReportPolicy = DEFAULT_POLICY) -> None:
    _validate_required_sections(dossier, policy)

    if _is_cannot_say_report(dossier):
        _validate_next_steps(dossier)
        tp = dossier.sections.get("target_profile", [])
        if not tp or not (tp[0].text or "").strip():
            raise PostValidateError("target_profile missing or empty for cannot_say_report.")
        return

    _validate_key_claims(dossier, policy)
    _validate_next_steps(dossier)
