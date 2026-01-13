import uuid
from app.schemas.fact import FactSet
from app.schemas.claim import ValidatedClaims, ValidatedClaim, EvidenceItem, RiskSignal

class ValidatorAgent:
    def run(self, facts: FactSet) -> ValidatedClaims:
        print(f"[Validator] Validating {len(facts.facts)} facts")
        
        # Mock: 모든 팩트를 기반으로 하나의 '주장'을 검증했다고 가정
        
        evidence_list = []
        for f in facts.facts:
            evidence_list.append(EvidenceItem(
                pmid=f.pmid,
                sentence_id=f.sentence_id,
                experiment_level=f.experiment.model if f.experiment else "unknown"
            ))

        return ValidatedClaims(
            claims=[
                ValidatedClaim(
                    claim_id=uuid.uuid4().hex,
                    normalized_claim="Target drug inhibits cell growth.",
                    evidence=evidence_list,
                    evidence_summary={"in_vitro": len(evidence_list), "in_vivo": 0, "clinical": 0},
                    consistency="consistent",  # Orchestrator 분기 처리에 중요 (consistent / conflicting / insufficient)
                    risk_signals=[] # Orchestrator가 체크함 (예: RiskSignal(type="toxicity", ...))
                )
            ]
        )