# schemas/query.py
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


StudyType = Literal["in_vitro", "in_vivo", "clinical", "review", "unknown"]


class SearchConstraints(BaseModel):
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    study_types: Optional[List[StudyType]] = None
    max_results: int = 50


class UserQuery(BaseModel):
    """
    사용자 자연어를 '구조화된 연구 질의'로 변환한 결과.
    Retriever의 쿼리 확장 / 검색 전략의 기준점.
    """
    query_id: str

    # 핵심: target은 Optional
    target_hint: Optional[str] = Field(
        default=None,
        description="User provided target hint (may be unknown/empty)"
    )

    disease: Optional[str] = None
    organ: Optional[str] = None

    intent: str = Field(
        ...,
        description="What user wants, e.g. 'identify therapeutic targets for migraine'"
    )
    hypothesis: Optional[str] = Field(
        default=None,
        description="Optional transfer question, e.g. 'applicable to other diseases?'"
    )

    constraints: Optional[SearchConstraints] = None
