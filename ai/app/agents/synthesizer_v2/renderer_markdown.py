from __future__ import annotations

from app.schemas.dossier import TargetDossier, DossierSection


def _fmt_section(title: str, sections: list[DossierSection]) -> list[str]:
    lines = []
    lines.append(f"## {title}")

    if not sections:
        lines.append("- (none)\n")
        return lines

    for sec in sections:
        if sec.text:
            lines.append(sec.text)
        if sec.citations:
            cites = ", ".join(sec.citations)
            lines.append(f"\n**Citations (PMID):** {cites}")
        lines.append("")

    return lines


def render_dossier_markdown(user_context: str, dossier: TargetDossier) -> str:
    lines: list[str] = []

    lines.append("# Target Dossier\n")
    lines.append(f"**Target:** {dossier.target}\n")

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
