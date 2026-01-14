# schemas/api.py
# 참고 : 내부 파이프라인에선 사용 안함
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal


class UserMessage(BaseModel):
    """
    UI/API 계층 입력.
    내부 파이프라인(UserQuery 등)으로 변환되기 전 단계.
    """
    session_id: str = Field(..., description="User session identifier")
    message: str = Field(..., description="Raw user message")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional UI context")


class SystemResponse(BaseModel):
    """
    UI/API 계층 출력.
    type은 프론트에서 렌더링/상태표시를 위해 사용.
    """
    type: Literal["ack", "question", "progress", "result", "warning", "error"]
    message: str
    payload: Optional[Dict[str, Any]] = None
