# DialogueAgent 전용

from pydantic import BaseModel
from typing import Optional, Dict


class UserMessage(BaseModel):
    session_id: str
    message: str
    context: Optional[Dict] = None


class SystemResponse(BaseModel):
    type: str  # ack | question | progress | result | warning
    message: str
    payload: Optional[Dict] = None
