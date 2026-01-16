from pydantic import BaseModel
from datetime import datetime
from uuid import UUID 

class SessionCreate(BaseModel):
    title: str = "새로운 세션"

class SessionResponse(BaseModel):
    id: UUID         
    user_email: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True