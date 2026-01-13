# app/agents/dialogue/state.py
from __future__ import annotations

from typing import TypedDict, Optional, Dict, Any

from app.schemas.message import UserMessage, SystemResponse
from app.schemas.user_query import UserQuery


class DialogueState(TypedDict, total=False):
    """
    LangGraph용 Dialogue 상태
    """
    user_message: UserMessage
    user_query: UserQuery

    # orchestrator 결과 (마지막 상태)
    orchestrator_result: Dict[str, Any]

    # 재검색 의사 확인
    awaiting_user_decision: bool
    user_decision: Optional[str]  # "yes" | "no"

    # 최종 사용자 응답
    response: SystemResponse

    # 에러 메시지(옵션)
    error: Optional[str]