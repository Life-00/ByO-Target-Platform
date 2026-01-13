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
    type: str  # increase | decrease | association | no_effect | unknown
    object: Optional[str] = None


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