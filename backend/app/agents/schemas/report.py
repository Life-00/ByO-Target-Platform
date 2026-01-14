# schemas/report.py
# Synthesizer 최종 산출물
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class RankedTarget(BaseModel):
    target: str
    rationale: str
    evidence_overview: Dict[str, int] = Field(
        default_factory=dict,
        description="e.g. {'clinical': 3, 'in_vivo': 2, 'review': 1}"
    )
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    citations: List[str] = Field(default_factory=list)  # pmid list


class TransferHypothesis(BaseModel):
    source_disease: str
    target: str
    candidate_diseases: List[str]
    reasoning: str
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    citations: List[str] = Field(default_factory=list)


class SynthesizedReport(BaseModel):
    """
    Synthesizer가 생성하는 '내용 결과'.
    렌더링은 별도 레이어에서 markdown/pdf로 변환.
    """
    report_id: str
    topic: str

    executive_summary: str
    ranked_targets: List[RankedTarget] = Field(default_factory=list)
    transfer_hypotheses: List[TransferHypothesis] = Field(default_factory=list)

    uncertainties: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

    citations: List[str] = Field(default_factory=list)  # pmid list (deduplicated)
