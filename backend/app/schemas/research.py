from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID  

class ResearchRequest(BaseModel):
    query: str
    top_k: int = 10
    is_confirmed: bool = False  # True면 바로 검색, False면 분석만 수행
    confirmed_intent: Optional[dict] = None # 분석된 의도 객체 (

class StagedPaperResponse(BaseModel):
    id: UUID           
    session_id: UUID   
    user_email: str
    source: str
    title: str
    authors: Optional[str] = None
    year: Optional[int] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    pdf_storage_path: Optional[str] = None
    score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True