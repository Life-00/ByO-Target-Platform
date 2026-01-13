import uuid
from app.schemas.claim import ValidatedClaims
from app.schemas.dossier import TargetDossier, DossierSection

class SynthesizerAgent:
    def run(self, claims: ValidatedClaims, target: str) -> TargetDossier:
        print(f"[Synthesizer] Writing dossier for {target}")
        
        return TargetDossier(
            dossier_id=uuid.uuid4().hex,
            target=target,
            format="markdown",
            sections={
                "Executive Summary": [
                    DossierSection(
                        text=f"This is a summary of {target}. It shows consistent efficacy.",
                        citations=[c.evidence[0].pmid for c in claims.claims if c.evidence]
                    )
                ],
                "Safety Profile": [
                    DossierSection(
                        text="No significant toxicity observed in preliminary studies.",
                        citations=[]
                    )
                ]
            }
        )