from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

# ✅ [신규] 요청 스키마 (Human-in-the-loop & 지시사항용)
class ExtractRequest(BaseModel):
    instruction: str = ""  # 예: "독성 관련 내용만 뽑아줘"
    is_confirmed: bool = False
    confirmed_instruction: Optional[str] = None


# ✅ [기존] 응답 스키마 (기존 코드 호환성을 위해 유지)
class ExtractResultItem(BaseModel):
    item_type: str
    item_id: UUID      
    status: str
    error: Optional[str] = None

class ExtractResponse(BaseModel):
    session_id: UUID   
    results: List[ExtractResultItem]