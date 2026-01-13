from pydantic import BaseModel
from typing import List, Dict, Any
from .citation import Citation

class PaperMeta(BaseModel):
    pmid: str
    title: str
    year: int | None = None
    url: str

class RiskSignal(BaseModel):
    type: str
    citation: Citation

class VectorHit(BaseModel):
    claim_id: str
    claim_text: str
    relation_type: str | None = None
    entities: Dict[str, Any] = {}
    evidence_level: str
    evidence: List[Citation]
    risk_signals: List[RiskSignal] = []
    paper: PaperMeta
    retrieval: Dict[str, Any] = {}
