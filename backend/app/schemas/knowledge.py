# # app/schemas/knowledge.py
# from __future__ import annotations
# from pydantic import BaseModel, Field
# from typing import Dict, Any, List, Optional, Union, Literal
#
# ChunkType = Literal[
#     "target",                # 타겟 자체 정보
#     "disease_target",        # 질병-타겟 관계 주장
#     "cross_disease",         # 다른 질병 전이 가능성
#     "risk_signal",           # 위험 신호
#     "claim",                 # 일반 주장 (Default)
# ]
#
# EvidenceLevel = Literal["in_vitro", "in_vivo", "clinical", "review", "unknown"]
#
# class KnowledgeChunk(BaseModel):
#     """
#     Vector DB에 저장되는 최소 의미 단위.
#     """
#     chunk_id: str
#     chunk_type: ChunkType = "claim"
#
#     # provenance
#     query_id: Optional[str] = None
#     pmid: str
#
#     # 핵심 엔티티
#     target: Optional[str] = None
#     disease: Optional[str] = None
#
#     # 주장/내용
#     claim: str = Field(..., description="Atomic claim to be retrieved and composed")
#
#     # ✅ 문자열(Literal) 또는 상세 객체(Dict) 모두 허용하도록 수정
#     stance: Optional[Union[Dict[str, Any], str]] = "unknown"
#     effect: Optional[Union[Dict[str, Any], str]] = None
#
#     evidence_level: Optional[str] = "unknown"
#     confidence: float = Field(0.5, ge=0.0, le=1.0)
#
#     # 메타데이터
#     metadata: Dict[str, Any] = Field(default_factory=dict)
#
# class KnowledgeDocument(BaseModel):
#     pmid: str
#     query_id: Optional[str] = None
#     extractor_version: str = "v1"
#     chunks: List[KnowledgeChunk] = Field(default_factory=list)

# schemas/knowledge.py
# Extractor 출력 + Vector DB 입력
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class KnowledgeChunk(BaseModel):
    """
    Vector DB에 저장되는 최소 의미 단위.
    Extractor(LLM)가 생성한 구조화된 주장 단위를 그대로 보존한다.
    """

    # ---- identity ----
    chunk_id: str
    chunk_type: str  # 예: "claim", "disease_target", "risk_signal" 등

    # ---- provenance ----
    query_id: Optional[str] = None
    pmid: str

    # ---- core entities ----
    target: Optional[str] = None
    disease: Optional[str] = None

    # ---- core claim ----
    claim: str = Field(..., description="Atomic claim extracted from paper")

    # ---- LLM-native structured interpretations ----
    effect: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Effect interpretation (direction, outcome, rationale, confidence)"
    )
    stance: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Author stance (polarity, strength, conditions)"
    )
    # salience: Optional[Dict[str, Any]] = Field(
    #     default=None,
    #     description="Claim importance within paper (level, reason)"
    # )

    # ---- evidence & confidence ----
    evidence_level: Optional[str] = Field(
        default="unknown",
        description="in_vitro | in_vivo | clinical | review | unknown"
    )
    confidence: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Overall confidence score from LLM"
    )

    # ---- auxiliary metadata ----
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional info for retrieval, filtering, synthesis"
        # 예: journal, year, species, assay, outcome_measure, notes 등
    )


class KnowledgeDocument(BaseModel):
    """
    한 논문에서 추출된 KnowledgeChunk 묶음.
    Vector DB에는 chunk 단위로 저장되고, 이 문서는 로그/저장용.
    """

    pmid: str
    query_id: Optional[str] = None
    extractor_version: str = "v2-llm-native"
    chunks: List[KnowledgeChunk] = Field(default_factory=list)