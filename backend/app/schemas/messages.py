from pydantic import BaseModel
from datetime import datetime

class MessageCreate(BaseModel):
    role: str   # "user" / "assistant" / "system"
    content: str

class MessageResponse(BaseModel):
    id: int
    session_id: str
    user_email: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
