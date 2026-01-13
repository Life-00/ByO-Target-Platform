from pydantic import BaseModel
from typing import Optional

class ReportRequest(BaseModel):
    prompt: str
    # 나중에 템플릿/포맷 추가 가능
    template: Optional[str] = None

class ReportResponse(BaseModel):
    session_id: str
    content: str
