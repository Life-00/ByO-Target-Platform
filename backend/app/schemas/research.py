from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ResearchRequest(BaseModel):
    query: str
    top_k: int = 10

class StagedPaperResponse(BaseModel):
    id: str
    session_id: str
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
