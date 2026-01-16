from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Citation(BaseModel):
    pmid: str
    url: str
    quote: str

class PaperMeta(BaseModel):
    pmid: str
    title: str
    year: Optional[int]
    url: str

class RiskSignal(BaseModel):
    type: str
    citation: Citation

class VectorHit(BaseModel):
    claim_id: str
    claim_text: str
    relation_type: str
    entities: Dict[str, Any] = {}
    evidence_level: str
    evidence: List[Citation]
    risk_signals: List[RiskSignal] = []
    paper: PaperMeta
    retrieval: Dict[str, Any] = {}