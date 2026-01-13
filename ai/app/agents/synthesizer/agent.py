from __future__ import annotations

from typing import Dict, List
from datetime import datetime

from app.schemas.claim import ValidatedClaims
from app.schemas.dossier import TargetDossier, DossierSection
from app.core.llm import generate_text  # 공용 LLM 사용


class SynthesizerAgent:
    """
    SynthesizerAgent
    ----------------
    - Input : ValidatedClaims
    - Output: TargetDossier
    - No decision / no policy / no interpretation
    """

    def _new_dossier_id(self) -> str:
        return datetime.now().strftime("d_%Y%m%d_%H%M%S")

    def to_target_dossier(
        self,
        validated: ValidatedClaims,
        *,
        target: str,
        dossier_id: str | None = None,
        format: str = "markdown",
    ) -> TargetDossier:

        if not validated or not isinstance(validated, ValidatedClaims):
            raise ValueError("Synthesizer expects ValidatedClaims")

        sections: Dict[str, List[DossierSection]] = {
            "key_claims": [],
            "risk_signals": [],
        }

        for claim in validated.claims:
            claim_pmids: List[str] = []

            for e in claim.evidence:
                if e.pmid:
                    claim_pmids.append(e.pmid)

            text_block = {
                "normalized_claim": claim.normalized_claim,
                "consistency": claim.consistency,
                "evidence_summary": claim.evidence_summary,
                "evidence": [
                    {
                        "pmid": e.pmid,
                        "sentence_id": e.sentence_id,
                        "experiment_level": e.experiment_level,
                    }
                    for e in claim.evidence
                ],
            }

            formatted_text = generate_text(str(text_block))

            sections["key_claims"].append(
                DossierSection(
                    text=formatted_text,
                    citations=sorted(set(claim_pmids)),
                )
            )

            risk_signals = claim.risk_signals or {}
            if isinstance(risk_signals, dict):
                for signal_type, signals in risk_signals.items():
                    for r in signals:
                        sections["risk_signals"].append(
                            DossierSection(
                                text=str(
                                    {
                                        "type": signal_type,
                                        "pmid": r.pmid,
                                        "sentence_id": r.sentence_id,
                                    }
                                ),
                                citations=[r.pmid] if r.pmid else [],
                            )
                        )

        return TargetDossier(
            dossier_id=dossier_id or self._new_dossier_id(),
            target=target or "Unknown Target",
            sections=sections,
            format=format,
        )

    def to_markdown(self, dossier: TargetDossier) -> str:
        md: List[str] = []
        md.append(f"# Target Dossier: {dossier.target}")
        md.append(f"- dossier_id: `{dossier.dossier_id}`")
        md.append("")

        for sec_name, sec_list in dossier.sections.items():
            md.append(f"## {sec_name}")
            for block in sec_list:
                md.append(block.text)
                if block.citations:
                    md.append(f"- citations(PMID): {', '.join(block.citations)}")
                md.append("")

        return "\n".join(md).strip() + "\n"

    def run(self, validated: ValidatedClaims, *, target: str) -> TargetDossier:
        return self.to_target_dossier(validated, target=target)
