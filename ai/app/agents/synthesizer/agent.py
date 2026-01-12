from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime

from app.schemas.claim import ValidatedClaims, ValidatedClaim
from app.schemas.dossier import TargetDossier, DossierSection


class SynthesizerAgent:
    """
    SynthesizerAgent
    ----------------
    - Input : ValidatedClaims
    - Output: TargetDossier (schema-only)
    - No decision / no policy / no interpretation
    """

    def _new_dossier_id(self) -> str:
        return datetime.now().strftime("d_%Y%m%d_%H%M%S")

    # Core mapping
    def to_target_dossier(
        self, validated: ValidatedClaims, *, target: str, dossier_id: str | None = None, format: str = "markdown",
    ) -> TargetDossier:

        if not validated or not isinstance(validated, ValidatedClaims):
            raise ValueError("Synthesizer expects ValidatedClaims")

        sections: Dict[str, List[DossierSection]] = {
            "key_claims": [],
            "risk_signals": [],
        }

        key_pmids: List[str] = []
        risk_pmids: List[str] = []

        # Key claims
        for claim in validated.claims:
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

            for e in claim.evidence:
                if e.pmid:
                    key_pmids.append(e.pmid)

            sections["key_claims"].append(
                DossierSection(
                    text=str(text_block),
                    citations=sorted(set(key_pmids)),
                )
            )

            # Risk signals
            for r in claim.risk_signals:
                sections["risk_signals"].append(
                    DossierSection(
                        text=str(
                            {
                                "type": r.type,
                                "pmid": r.pmid,
                                "sentence_id": r.sentence_id,
                            }
                        ),
                        citations=[r.pmid] if r.pmid else [],
                    )
                )
                if r.pmid:
                    risk_pmids.append(r.pmid)

        return TargetDossier(
            dossier_id=dossier_id or self._new_dossier_id(),
            target=target or "Unknown Target",
            sections=sections,
            format=format,
        )

    # Optional: developer convenience
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

    def run(self,validated: ValidatedClaims, *, target: str,
    ) -> TargetDossier:
        return self.to_target_dossier(validated, target=target)