from pydantic import BaseModel
from typing import List
from datetime import datetime

class SelectionItem(BaseModel):
    item_type: str   # "uploaded_file" / "staged_paper"
    item_id: str

class SelectionsUpsertRequest(BaseModel):
    items: List[SelectionItem]

class SelectionResponse(BaseModel):
    id: str
    session_id: str
    user_email: str
    item_type: str
    item_id: str
    created_at: datetime

    class Config:
        from_attributes = True
