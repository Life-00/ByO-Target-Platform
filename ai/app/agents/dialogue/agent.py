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

from app.core.llm import llm_client, DEFAULT_LLM_MODEL


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
    def _build_graph(self):
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
        return g.compile()

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

        # Yes/No 응답 판단
        decision = self._parse_yes_no(text)
        if decision:
            state["user_decision"] = decision
            return state

        # 사용자 질의 파싱
        parsed = self._parse_user_text(text)
        if not parsed:
            state["response"] = SystemResponse(
                type="warning",
                message="요청을 해석할 수 없습니다. 타깃과 질환을 포함해 질문을 함께 알려주세요.",
                payload=None,
            )
            return state

        # 필수 필드 검증
        missing = []
        if not parsed.get("target"):
            missing.append("타깃(유전자/단백질)")
        if not parsed.get("question"):
            missing.append("검증 질문")

        if missing:
            state["response"] = SystemResponse(
                type="question",
                message=f"다음 정보가 필요합니다: {', '.join(missing)}",
                payload={"missing": missing},
            )
            return state

        # UserQuery 생성
        uq = UserQuery(
            query_id=str(uuid.uuid4()),
            target=parsed.get("target"),
            disease=parsed.get("disease"),
            organ=parsed.get("organ"),
            research_question=parsed.get("question"),
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
        # 1. user_query 안전 확인
        uq = state.get("user_query")
        if not uq:
            state["response"] = SystemResponse(
                type="warning",
                message="질의 정보가 누락되어 분석을 진행할 수 없습니다. 다시 시도해 주세요.",
                payload=None,
            )
            return state

        # 2. Orchestrator 실행 보호
        try:
            result = self.orchestrator.run(user_query=uq)
        except Exception as e:
            state["response"] = SystemResponse(
                type="error",
                message="연구 근거 분석 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                payload={"error": str(e)},
            )
            return state

        state["orchestrator_result"] = result

        # 3. 추가 검색 필요 여부
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

        # 4. 최종 요약 → LLM
        prompt = self._render_result_message(
            result.get("validation_summary")
        )
        final_text = self._call_llm(prompt)

        state["response"] = SystemResponse(
            type="result",
            message=final_text,
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

            # state["response"] = SystemResponse(
            #     type="result",
            #     message=self._render_result_message(
            #         result.get("validation_summary")
            #     ),
            #     payload={"re_retrieved": True},
            # )
            prompt = self._render_result_message(
                result.get("validation_summary")
            )
            final_text = self._call_llm(prompt)

            state["response"] = SystemResponse(
                type="result",
                message=final_text,
                payload=None,
            )

            return state

        # 사용자가 재검색 NO
        summary = orch.get("validation_summary") if orch else None
        prompt = self._render_result_message(summary)
        final_text = self._call_llm(prompt)

        state["response"] = SystemResponse(
            type="result",
            message=final_text,
            payload={"finalized": True},
        )
        return state

    # -----------------------
    # Router
    # -----------------------
    def route_after_parse(self, state: DialogueState) -> str:
        # 1. Yes/No 응답
        if state.get("user_decision"):
            return "handle_decision"

        resp = state.get("response")

        # 2. 사용자에게 질문하거나 경고한 상태면 종료
        if resp and resp.type in {"question", "warning"}:
            return "ask_clarify"

        # 3. user_query가 있어야만 pipeline 가능
        if "user_query" in state:
            return "run_pipeline"

        # 4. 안전장치 (여기 오면 설계 오류)
        return "ask_clarify"


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
        target_match = re.search(r"[A-Z]{2,}[0-9\-]*", text)
        target = target_match.group(0) if target_match else None

        # disease 후보(휴리스틱): "~암", "~질환", "~증" 등
        disease_match = re.search(r"([가-힣A-Za-z0-9\-]+(?:암|질환|증|병))", text)
        disease = disease_match.group(1) if disease_match else None

        # organ 후보 (폐, 간, 뇌 등)
        organ_match = re.search(r"(폐|간|뇌|위|대장|유방)", text)
        organ = organ_match.group(1) if organ_match else None

        # question은 전체 문장
        question = text.strip()

        return {
            "target": target,
            "disease": disease,
            "organ": organ,
            "question": question,
            "retmax": 5,
            "date_from": None,
            "date_to": None,
        }

    # -----------------------
    # Helpers: 메시지 rendering (LLM 이용)
    # -----------------------
    def _render_result_message(self, summary: Dict[str, Any] | None) -> str:
        """
        validation_summary → LLM 프롬프트 생성
        """
        if not summary:
            return (
                "검증 결과 요약 정보가 없습니다. "
                "사용자에게 현재 상태를 간단히 설명해 주세요."
            )

        return self._build_summary_prompt(summary)

    def _build_summary_prompt(self, summary: Dict[str, Any]) -> str:
        n = summary.get("n_claims", 0)
        c = summary.get("n_consistent", 0)
        cf = summary.get("n_conflicting", 0)
        ins = summary.get("n_insufficient", 0)
        risk_counts = summary.get("risk_counts", {}) or {}

        risk_desc = ""
        if risk_counts:
            items = [f"{k}: {v}건" for k, v in risk_counts.items()]
            risk_desc = "위험 신호 요약: " + ", ".join(items)

        return f"""
        너는 바이오메디컬 연구 근거를 사용자에게 설명하는 전문가이다.
    
        아래는 한 치료 타깃에 대한 연구 검증 요약 결과이다.
    
        - 전체 주장 수: {n}
        - 근거가 일관된 주장: {c}
        - 서로 상충되는 주장: {cf}
        - 근거가 충분하지 않은 주장: {ins}
    
        {risk_desc}
    
        요청:
        1. 위 정보를 바탕으로 사용자가 이해할 수 있도록 자연스럽게 요약하라.
        2. 연구 근거의 신뢰도를 중심으로 설명하라.
        3. 과도한 확정 표현은 피하고, 전문가적이지만 친절한 어조를 사용하라.
        4. 마지막에 “추가로 상세 근거(PMID, 실험 수준)를 요청할 수 있음”을 안내하라.
        5. 불확실성이 있는 경우, 그 이유를 명시적으로 언급하라.
        """


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

    def _call_llm(self, prompt: str, mode: str = "result") -> str:

        system_prompt = (
            "너는 신약 타깃 검증 결과를 설명하는 바이오메디컬 어시스턴트이다."
            if mode == "result"
            else "너는 사용자의 추가 선택을 유도하는 연구 보조 어시스턴트이다."
        )

        try:
            response = llm_client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content

        except Exception as e:
            print(e)
            return (
                "현재 결과를 생성하는 중 오류가 발생했습니다.\n"
                "잠시 후 다시 시도해 주세요."
            )