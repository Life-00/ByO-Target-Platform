# Extractor Agent의 출력

from pydantic import BaseModel
from typing import List, Optional


class EntitySet(BaseModel):
    target: List[str] = []
    disease: List[str] = []
    organ: List[str] = []
    compound: List[str] = []


class ExperimentInfo(BaseModel):
    model: str  # cell | animal | human | unknown
    species: str  # mouse | rat | human | unknown
    assay: Optional[str] = None


class RelationInfo(BaseModel):
    stance: str # support | refute | neutral | unknown
    effect: str # increase | decrease | no_change | mixed | unknown
    outcome: Optional[str] = None # tumor_growth | survival | expression | activity | unknown
    evidence_strength: str # in_vitro | in_vivo | clinical | review | unknown
    confidence: Optional[float] = None # 0.0 ~ 1.0 (LLM 추정)
    rationale: Optional[str] = None


class Fact(BaseModel):
    fact_id: str
    pmid: str
    sentence_id: str
    text: str
    entities: EntitySet
    experiment: ExperimentInfo
    relation: RelationInfo


class FactSet(BaseModel):
    facts: List[Fact]