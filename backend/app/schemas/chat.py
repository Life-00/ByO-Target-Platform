from typing import List, Optional, Any
from pydantic import BaseModel
from uuid import UUID

class ContextItem(BaseModel):
    id: str              # 파일 ID
    type: str            # "uploaded_file" 또는 "staged_paper"
    status: str          # "indexed", "uploaded" 등
    title: str           # 파일 제목 (가장 중요)
    
class ContextItem(BaseModel):
    id: str              # UUID string
    type: str            # "uploaded_file" | "staged_paper"
    status: str          # "indexed" | "uploaded" | "staged"
    title: str           # 파일명 또는 논문 제목

class ChatRequest(BaseModel):
    message: str
    # 기존 context_ids 대신 context_items를 주력으로 사용
    context_ids: Optional[List[str]] = None 
    context_items: Optional[List[ContextItem]] = None # ✅ 추가됨