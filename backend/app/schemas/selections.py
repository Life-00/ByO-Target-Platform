from pydantic import BaseModel
from typing import List
from datetime import datetime
from uuid import UUID  

class SelectionItem(BaseModel):
    item_type: str
    item_id: UUID      

class SelectionsUpsertRequest(BaseModel):
    items: List[SelectionItem]

class SelectionResponse(BaseModel):
    id: UUID           
    session_id: UUID   
    user_email: str
    item_type: str
    item_id: UUID      
    created_at: datetime

    class Config:
        from_attributes = True