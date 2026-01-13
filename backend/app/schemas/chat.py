from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    context_ids: Optional[List[str]] = []  