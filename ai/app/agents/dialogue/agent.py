# app/agents/dialogue/agent.py
from __future__ import annotations

import re
import uuid
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from app.schemas.message import UserMessage, SystemResponse
from app.schemas.user_query import UserQuery, SearchConstraints
from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.dialogue.state import DialogueState


class DialogueAgent:
    """
    DialogueAgent
    - 사용자 메시지 파싱
    - 누락 정보 질문
    - Orchestrator 실행
    - Orchestrator 결과를 사용자 메시지로 변환
    - 재검색 여부를 사용자에게 질문
    """

    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.graph = self._build_graph()

    # -----------------------
    # Graph
    # -----------------------
    def _build_graph(self) -> StateGraph:
        g = StateGraph(DialogueState)

        g.add_node("parse", self.node_parse)
        g.add_node("route", self.node_route)
        g.add_node("run_pipeline", self.node_run_pipeline)
        g.add_node("handle_decision", self.node_handle_decision)

        g.set_entry_point("parse")
        g.add_edge("parse", "route")

        g.add_conditional_edges(
            "route",
            self.route_after_parse,
            {
                "ask_clarify": END,
                "run_pipeline": "run_pipeline",
                "handle_decision": "handle_decision",
            },
        )

        g.add_edge("run_pipeline", END)
        g.add_edge("handle_decision", END)
        return g

    # -----------------------
    # Public entry
    # -----------------------
    def run(self, user_message: UserMessage) -> SystemResponse:
        state: DialogueState = {"user_message": user_message}
        final_state = self.graph.invoke(state)
        return final_state["response"]

    # -----------------------
    # Nodes
    # -----------------------
    def node_parse(self, state: DialogueState) -> DialogueState:
        um = state["user_message"]
        text = getattr(um, "text", None) or getattr(um, "message", None) or ""

        # Yes/No 응답 감지
        decision = self._parse_yes_no(text)
        if decision:
            state["user_decision"] = decision
            return state

        parsed = self._parse_user_text(text)
        if not parsed:
            state["response"] = SystemResponse(
                type="warning",
                message="요청을 해석할 수 없습니다. 타깃(유전자/단백질)과 질환, 질문을 함께 알려주세요.",
                payload=None,
            )
            return state

        # UserQuery 구성
        uq = UserQuery(
            query_id=str(uuid.uuid4()),
            target=parsed.get("target"),
            disease=parsed.get("disease"),
            question=parsed.get("question"),
            constraints=SearchConstraints(
                retmax=parsed.get("retmax", 5),
                date_from=parsed.get("date_from"),
                date_to=parsed.get("date_to"),
            ),
        )
        state["user_query"] = uq
        return state

    def node_route(self, state: DialogueState) -> DialogueState:
        # 재검색 결정 응답이면 handle_decision으로
        if state.get("user_decision"):
            return state

        uq = state.get("user_query")
        if not uq:
            state["response"] = SystemResponse(
                type="warning",
                message="요청을 해석할 수 없습니다. 타깃과 질환을 포함해 다시 입력해 주세요.",
                payload=None,
            )
            return state

        # 누락 정보 확인: target/disease/question 중 하나라도 없으면 질문
        missing = []
        if not getattr(uq, "target", None):
            missing.append("타깃(유전자/단백질)")
        if not getattr(uq, "disease", None):
            missing.append("질환")
        if not getattr(uq, "question", None):
            missing.append("검증 질문")

        if missing:
            state["response"] = SystemResponse(
                type="question",
                message=f"다음 정보가 필요합니다: {', '.join(missing)}. 예: 'EGFR의 폐암에서 효능 근거를 검증해줘'",
                payload={"missing": missing},
            )
            return state

        # 충분하면 pipeline 실행
        state["response"] = SystemResponse(
            type="info",
            message="요청을 확인했습니다. 연구 근거를 수집하고 핵심 주장 단위로 정리하겠습니다.",
            payload={"query_id": uq.query_id},
        )
        return state

    def node_run_pipeline(self, state: DialogueState) -> DialogueState:
        uq = state["user_query"]

        result = self.orchestrator.run(uq)
        state["orchestrator_result"] = result

        if result.get("need_more_retrieval"):
            state["awaiting_user_decision"] = True
            state["response"] = SystemResponse(
                type="question",
                message=self._render_need_more_message(
                    result.get("validation_summary"),
                    result.get("retrieval_hint"),
                ),
                payload=None,
            )
            return state

        # 충분한 경우 → 바로 결과 제공
        state["response"] = SystemResponse(
            type="result",
            message=self._render_result_message(
                result.get("validation_summary")
            ),
            payload=None,
        )
        return state

    def node_handle_decision(self, state: DialogueState) -> DialogueState:
        decision = state.get("user_decision")
        orch = state.get("orchestrator_result")

        # 사용자가 재검색 YES
        if decision == "yes":
            # 🔁 Orchestrator 재실행 (facts 없이 → retriever부터)
            uq = orch.get("user_query") if orch else state.get("user_query")
            result = self.orchestrator.run(user_query=uq)
            state["orchestrator_result"] = result

            state["response"] = SystemResponse(
                type="result",
                message=self._render_result_message(
                    result.get("validation_summary")
                ),
                payload={"re_retrieved": True},
            )
            return state

        # 사용자가 재검색 NO
        summary = orch.get("validation_summary") if orch else None
        state["response"] = SystemResponse(
            type="result",
            message=self._render_result_message(summary),
            payload={"finalized": True},
        )
        return state

    # -----------------------
    # Router
    # -----------------------
    def route_after_parse(self, state: DialogueState) -> str:
        if state.get("user_decision"):
            return "handle_decision"
        resp = state.get("response")
        if resp and resp.type == "question":
            return "ask_clarify"
        return "run_pipeline"

    # -----------------------
    # Helpers: 사용자 질의 parsing
    # -----------------------
    def _parse_yes_no(self, text: str) -> str | None:
        text = text.strip().lower()
        if text in {"예", "네", "yes", "y"}:
            return "yes"
        if text in {"아니오", "아니요", "no", "n"}:
            return "no"
        return None


    def _parse_user_text(self, text: str) -> Dict[str, Any]:
        """
        매우 단순 파서(MVP):
        - target: 대문자 유전자/단백질 토큰(예: EGFR, TP53)
        - disease: '에서', '관련', '질환' 주변 단어(heuristic)
        - question: 전체 문장
        """

        # target 후보: 대문자+숫자/하이픈 (EGFR, BRCA1, PD-1 등)
        target_match = re.search(r"\b[A-Z0-9\-]{3,}\b", text)
        target = target_match.group(0) if target_match else None

        # disease 후보(휴리스틱): "~암", "~질환", "~증" 등
        disease_match = re.search(r"([가-힣A-Za-z0-9\-]+(?:암|질환|증|병))", text)
        disease = disease_match.group(1) if disease_match else None

        # question은 전체 문장
        question = text.strip()

        return {
            "target": target,
            "disease": disease,
            "question": question,
            "retmax": 5,
            "date_from": None,
            "date_to": None,
        }

    # -----------------------
    # Helpers: message rendering
    # -----------------------
    def _render_result_message(self, summary: Dict[str, Any] | None) -> str:
        """
        validation_summary → 사용자 결과 메시지
        """
        if not summary:
            return "검증 결과를 정리했습니다. (요약 정보가 비어 있습니다.)"

        n = summary.get("n_claims", 0)
        c = summary.get("n_consistent", 0)
        cf = summary.get("n_conflicting", 0)
        ins = summary.get("n_insufficient", 0)
        risk_counts = summary.get("risk_counts", {}) or {}

        risk_part = ""
        if risk_counts:
            # risk type별 카운트 나열
            items = [f"{k} {v}건" for k, v in risk_counts.items()]
            risk_part = f"\n- 위험 신호(키워드) 탐지: {', '.join(items)}"

        return (
            f"핵심 주장 {n}개를 기준으로 근거를 정리했습니다.\n"
            f"- 일관됨: {c}개\n"
            f"- 상충됨: {cf}개\n"
            f"- 근거 부족: {ins}개"
            f"{risk_part}\n\n"
            "원하시면 주장별 근거(PMID)와 실험 수준(in vitro/in vivo/clinical)까지 상세히 보여드릴게요."
        )

    def _render_need_more_message(self, summary: Dict[str, Any] | None, hint: str | None) -> str:
        """
        need_more_retrieval=True일 때 사용자 질문 메시지
        """
        base = "현재 확보된 근거만으로는 결론을 내리기 어렵습니다."

        if summary:
            cf = summary.get("n_conflicting", 0)
            ins = summary.get("n_insufficient", 0)
            base += f"\n- 상충됨: {cf}개, 근거 부족: {ins}개"

        if hint:
            # 기계적 hint를 사람말로 약간 부드럽게
            base += f"\n- 추가 확인이 필요한 이유: {hint}"

        base += "\n\n추가 논문을 더 검색해서 근거를 보강할까요? (예/아니오)"
        return base
