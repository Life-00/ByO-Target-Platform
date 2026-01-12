# app/agents/dialogue/agent.py
from __future__ import annotations

import re
import uuid
from typing import TypedDict, Optional, Dict, Any

from langgraph.graph import StateGraph, END

from app.schemas.message import UserMessage, SystemResponse
from app.schemas.user_query import UserQuery, SearchConstraints
from app.agents.orchestrator.agent import OrchestratorAgent


class DialogueState(TypedDict, total=False):
    user_message: UserMessage
    user_query: Optional[UserQuery]
    response: Optional[SystemResponse]
    error: Optional[str]


def _parse_user_query_rule(message: str) -> Dict[str, Any]:
    """
    MVP rule-based parsing.
    - target: 대문자 약어(예: TNF, EGFR) 또는 'Target:' 패턴
    - disease: 'disease:' 패턴
    """
    target = None
    disease = None

    m = re.search(r"(?:target\s*:\s*)([A-Za-z0-9\-_/]+)", message, flags=re.I)
    if m:
        target = m.group(1).strip()

    m = re.search(r"(?:disease\s*:\s*)(.+)$", message, flags=re.I)
    if m:
        disease = m.group(1).strip()

    # 아주 단순한 백업: 대문자 약어 후보 하나를 target로
    if not target:
        caps = re.findall(r"\b[A-Z0-9\-]{3,}\b", message)
        if caps:
            target = caps[0]

    return {"target": target, "disease": disease}


def node_parse(state: DialogueState) -> DialogueState:
    msg = state["user_message"].message
    parsed = _parse_user_query_rule(msg)

    # research_question은 원문 그대로 두되, 타깃/질환이 없으면 아직 미완성
    uq = UserQuery(
        query_id=str(uuid.uuid4()),
        target=parsed["target"] or "UNKNOWN",
        disease=parsed["disease"],
        organ=None,
        research_question=msg,
        constraints=SearchConstraints(max_results=50),
    )
    state["user_query"] = uq
    return state


def node_route(state: DialogueState) -> DialogueState:
    uq = state.get("user_query")
    if uq is None:
        state["response"] = SystemResponse(
            type="warning",
            message="요청을 해석할 수 없습니다.",
            payload=None,
        )
        return state

    # 최소 기준: target이 UNKNOWN이면 명확화 질문
    if uq.target == "UNKNOWN" or uq.target.strip() == "":
        state["response"] = SystemResponse(
            type="question",
            message="분석할 타깃(예: EGFR, TNF 등)을 지정해 주세요. 예) target: EGFR",
            payload=None,
        )
        return state

    # disease는 optional로 두되, 너무 모호하면 한 번 더 질문할 수도 있음(선택)
    if uq.disease is None or uq.disease.strip() == "":
        state["response"] = SystemResponse(
            type="question",
            message="질환 범위를 지정해 주실래요? 예) disease: Alzheimer's disease (선택이지만 권장)",
            payload={"query_id": uq.query_id},
        )
        return state

    # 실행 단계로 넘김 (response는 아직 비워둠)
    state["response"] = None
    return state


def node_run_pipeline(state: DialogueState) -> DialogueState:
    # route에서 question이 생성됐다면 실행하지 않음
    if state.get("response") is not None:
        return state

    orchestrator = OrchestratorAgent()

    uq = state["user_query"]
    dossier = orchestrator.run(uq)

    state["response"] = SystemResponse(
        type="result",
        message="타깃 검증 리포트가 생성되었습니다.",
        payload={
            "query_id": uq.query_id,
            "dossier_id": dossier.dossier_id,
        },
    )
    return state


def build_dialogue_graph():
    g = StateGraph(DialogueState)

    g.add_node("parse", node_parse)
    g.add_node("route", node_route)
    g.add_node("run_pipeline", node_run_pipeline)

    g.set_entry_point("parse")
    g.add_edge("parse", "route")

    # route 단계에서 response가 있으면 END, 없으면 실행
    def _route_condition(state: DialogueState) -> str:
        return "end" if state.get("response") is not None else "run"

    g.add_conditional_edges(
        "route",
        _route_condition,
        {
            "end": END,
            "run": "run_pipeline",
        },
    )

    g.add_edge("run_pipeline", END)
    return g.compile()


class DialogueAgent:
    def __init__(self):
        self.graph = build_dialogue_graph()

    def handle(self, user_message: UserMessage) -> SystemResponse:
        final_state = self.graph.invoke({"user_message": user_message})
        return final_state["response"]
