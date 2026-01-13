# schemas/knowledge.py
# Extractor 출력 + Vector DB 입력
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal


ChunkType = Literal[
    "target",                # 타겟 자체 정보(정의/역할/기전 등)
    "disease_target",        # 질병-타겟 관계 주장(효과/근거)
    "cross_disease",         # 다른 질병으로의 전이 가능성
    "risk_signal",           # 독성/실패/불일치 등 위험 신호
]

EvidenceLevel = Literal["in_vitro", "in_vivo", "clinical", "review", "unknown"]
Stance = Literal["support", "refute", "neutral", "unknown"]
Effect = Literal["increase", "decrease", "no_change", "mixed", "unknown"]


class KnowledgeChunk(BaseModel):
    """
    Vector DB에 저장되는 최소 의미 단위.
    검색/재조합/필터링을 위해 metadata를 풍부하게 가진다.
    """
    chunk_id: str
    chunk_type: ChunkType

    # provenance
    query_id: Optional[str] = None
    pmid: str

    # 핵심 엔티티(최소)
    target: Optional[str] = None
    disease: Optional[str] = None

    # 주장/내용(자연어는 '짧고 단정한 claim' 중심)
    claim: str = Field(..., description="Atomic claim to be retrieved and composed")
    stance: Stance = "unknown"
    effect: Effect = "unknown"

    evidence_level: EvidenceLevel = "unknown"
    confidence: float = Field(0.5, ge=0.0, le=1.0)

    # retrieval+composition을 위한 부가정보
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # 예: species, assay, population, endpoints, dose, comparator, notes, speculativeness 등


class KnowledgeDocument(BaseModel):
    """
    Extractor가 한 논문에서 뽑은 chunk 묶음.
    (Vector DB에는 각 chunk가 개별로 들어가고, 이 문서는 저장/로그용)
    """
    pmid: str
    query_id: Optional[str] = None
    extractor_version: str = "v1"
    chunks: List[KnowledgeChunk] = Field(default_factory=list)
