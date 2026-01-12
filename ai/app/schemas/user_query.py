# 사용자 의도를 구조화된 연구 질의로 변환한 결과

from pydantic import BaseModel
from typing import List, Optional


class SearchConstraints(BaseModel):
    year_from: Optional[int] = None
    study_types: Optional[List[str]] = None  # in vitro, in vivo, clinical
    max_results: int = 50


class UserQuery(BaseModel):
    query_id: str
    target: str
    disease: Optional[str] = None
    organ: Optional[str] = None
    research_question: str
    constraints: Optional[SearchConstraints] = None