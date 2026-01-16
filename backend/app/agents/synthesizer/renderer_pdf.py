from __future__ import annotations

from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from app.schemas.dossier import TargetDossier


def render_dossier_pdf(dossier: TargetDossier) -> bytes:
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Target Dossier - {dossier.target}",
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Target Dossier</b>", styles["Title"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"<b>Target:</b> {dossier.target}", styles["BodyText"]))
    story.append(Spacer(1, 8 * mm))

    ordered_keys = [
        "target_profile",
        "key_claims",
        "evidence_level_summary",
        "risk_signals",
        "next_validation_steps",
    ]

    for key in ordered_keys:
        story.append(Paragraph(key.replace("_", " ").title(), styles["Heading2"]))
        story.append(Spacer(1, 4 * mm))

        for sec in dossier.sections.get(key, []):
            body = (sec.text or "").replace("\n", "<br/>")
            story.append(Paragraph(body, styles["BodyText"]))

            if sec.citations:
                cites = ", ".join(sec.citations)
                story.append(Paragraph(f"<i>PMID:</i> {cites}", styles["BodyText"]))

            story.append(Spacer(1, 6 * mm))

        story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()
