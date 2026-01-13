# schemas/deprecated.py
# 나중에 필요해질 수도 있으니 남겨둠
from __future__ import annotations

from pydantic import BaseModel
from typing import List, Dict, Literal


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
    evidence_summary: Dict[str, int]
    consistency: Literal["consistent", "conflicting", "insufficient"]
    risk_signals: List[RiskSignal] = []


class ValidatedClaims(BaseModel):
    claims: List[ValidatedClaim]
