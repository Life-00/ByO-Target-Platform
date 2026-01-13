# Validator Agent의 결과

from pydantic import BaseModel
from typing import List, Dict


class EvidenceItem(BaseModel):
    pmid: str
    sentence_id: str
    experiment_level: str  # in vitro | in vivo | clinical


class RiskSignal(BaseModel):
    type: str  # toxicity | failure | inconsistency
    pmid: str
    sentence_id: str


class ValidatedClaim(BaseModel):
    claim_id: str
    normalized_claim: str

    evidence: List[EvidenceItem]

    evidence_summary: Dict[str, int]  # {"in_vitro": 3, "in_vivo": 1, "clinical": 0}

    consistency: str  # consistent | conflicting | insufficient

    risk_signals: List[RiskSignal] = []


class ValidatedClaims(BaseModel):
    claims: List[ValidatedClaim]
