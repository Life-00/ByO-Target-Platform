from pydantic import BaseModel
from datetime import datetime
from uuid import UUID  

class MessageCreate(BaseModel):
    role: str
    content: str

class MessageResponse(BaseModel):
    id: int            
    session_id: UUID   
    user_email: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True