from pydantic import BaseModel
from typing import Optional
from uuid import UUID  

class ReportRequest(BaseModel):
    prompt: str
    template: Optional[str] = None

class ReportResponse(BaseModel):
    session_id: UUID   
    content: str