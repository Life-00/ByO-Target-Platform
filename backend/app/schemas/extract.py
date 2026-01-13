from pydantic import BaseModel
from typing import List, Optional

class ExtractResultItem(BaseModel):
    item_type: str
    item_id: str
    status: str
    error: Optional[str] = None

class ExtractResponse(BaseModel):
    session_id: str
    results: List[ExtractResultItem]
