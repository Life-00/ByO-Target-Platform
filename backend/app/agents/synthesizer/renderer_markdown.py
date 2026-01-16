# app/agents/synthesizer/renderer_markdown.py
from __future__ import annotations
from app.schemas.dossier import TargetDossier, DossierSection

def _fmt_section(title: str, sections: list[DossierSection]) -> list[str]:
    lines = []
    lines.append(f"## {title}")

    if not sections:
        lines.append("- (추출된 데이터 없음)\n")
        return lines

    for sec in sections:
        if sec.text:
            lines.append(sec.text)
        if sec.citations:
            cites = ", ".join(sec.citations)
            lines.append(f"\n**참조 문헌 (PMID):** {cites}")
        lines.append("")

    return lines

def render_dossier_markdown(user_context: str, dossier: TargetDossier) -> str:
    """
    Dossier 객체를 최종 마크다운 문자열로 렌더링합니다.
    """
    lines: list[str] = []

    lines.append(f"# Target Validation Dossier: {dossier.target}\n")
    lines.append(f"**연구 목적/맥락:** {user_context[:100]}...\n")

    # 보고서 목차 순서 정의
    ordered_keys = [
        "target_profile",
        "key_claims",
        "evidence_level_summary",
        "risk_signals",
        "next_validation_steps",
    ]

    for key in ordered_keys:
        sections = dossier.sections.get(key, [])
        title = key.replace("_", " ").title()
        lines.extend(_fmt_section(title, sections))

    return "\n".join(lines)