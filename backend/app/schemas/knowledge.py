# app/schemas/knowledge.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union, Literal

ChunkType = Literal[
    "target",                # 타겟 자체 정보
    "disease_target",        # 질병-타겟 관계 주장
    "cross_disease",         # 다른 질병 전이 가능성
    "risk_signal",           # 위험 신호
    "claim",                 # 일반 주장 (Default)
]

EvidenceLevel = Literal["in_vitro", "in_vivo", "clinical", "review", "unknown"]

class KnowledgeChunk(BaseModel):
    """
    Vector DB에 저장되는 최소 의미 단위.
    """
    chunk_id: str
    chunk_type: ChunkType = "claim"

    # provenance
    query_id: Optional[str] = None
    pmid: str

    # 핵심 엔티티
    target: Optional[str] = None
    disease: Optional[str] = None

    # 주장/내용
    claim: str = Field(..., description="Atomic claim to be retrieved and composed")

    # ✅ 문자열(Literal) 또는 상세 객체(Dict) 모두 허용하도록 수정
    stance: Optional[Union[Dict[str, Any], str]] = "unknown"
    effect: Optional[Union[Dict[str, Any], str]] = None

    evidence_level: Optional[str] = "unknown"
    confidence: float = Field(0.5, ge=0.0, le=1.0)

    # 메타데이터
    metadata: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeDocument(BaseModel):
    pmid: str
    query_id: Optional[str] = None
    extractor_version: str = "v1"
    chunks: List[KnowledgeChunk] = Field(default_factory=list)