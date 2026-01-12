from typing import Optional
from app.schemas.user_query import UserQuery


class DialogueState:
    def __init__(self):
        self.current_query: Optional[UserQuery] = None