from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID 

class ExtractResultItem(BaseModel):
    item_type: str
    item_id: UUID      
    status: str
    error: Optional[str] = None

class ExtractResponse(BaseModel):
    session_id: UUID   
    results: List[ExtractResultItem]