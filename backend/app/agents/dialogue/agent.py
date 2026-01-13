from __future__ import annotations

import json
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
    - 사용자 메시지 파싱 (LLM 기반: 분석 요청 vs 일상 대화 구분)
    - 누락 정보 질문
    - Orchestrator 실행
    - 결과 종합
    """

    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.graph = self._build_graph()

    # -----------------------
    # Graph Construction
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
                "end_turn": END,              # 일상 대화, 질문, 경고 등 즉시 종료
                "run_pipeline": "run_pipeline", 
                "handle_decision": "handle_decision", 
            },
        )

        g.add_edge("run_pipeline", END)
        g.add_edge("handle_decision", END)
        return g.compile()

    # -----------------------
    # Public Entry
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

        # 1. Yes/No 응답 판단
        decision = self._parse_yes_no(text)
        if decision:
            state["user_decision"] = decision
            return state

        # 2. 사용자 질의 파싱 (의도 분류 포함)
        parsed = self._llm_parse_user_text(text)
        
        if not parsed:
            state["response"] = SystemResponse(
                type="warning",
                message="죄송합니다. 요청을 이해하지 못했습니다.",
                payload=None,
            )
            return state

        # [NEW] 4번 기능 구현: 의도가 'general_chat'이면 바로 응답하고 종료
        if parsed.get("intent_type") == "general_chat":
            # 가벼운 인사는 LLM이 생성한 답변을 그대로 사용
            chat_response = parsed.get("response") or "네, 안녕하세요! 무엇을 도와드릴까요?"
            state["response"] = SystemResponse(
                type="chat", # 프론트엔드에서 일반 텍스트로 처리
                message=chat_response,
                payload=None,
            )
            return state

        # 3. 필수 필드 검증 (intent_type == 'analysis' 인 경우만)
        missing = []
        if not parsed.get("target"):
            missing.append("타깃(유전자/약물)")
        if not parsed.get("question"):
            missing.append("연구 질문")

        if missing:
            state["response"] = SystemResponse(
                type="question",
                message=f"분석을 위해 다음 정보가 필요합니다: {', '.join(missing)}",
                payload={"missing": missing},
            )
            return state

        # 4. UserQuery 객체 생성
        uq = UserQuery(
            query_id=str(uuid.uuid4()),
            target=parsed["target"],
            disease=parsed.get("disease"),
            organ=parsed.get("organ"),
            research_question=parsed["question"],
            constraints=SearchConstraints(
                retmax=5,
                year_from=parsed.get("year_from"),
            )
        )

        state["user_query"] = uq
        return state

    def node_route(self, state: DialogueState) -> DialogueState:
        # 이미 앞단에서 응답(일상대화/질문/경고)이 생성되었다면 종료
        if state.get("response"):
            return "end_turn"

        # 재검색 결정
        if state.get("user_decision"):
            return state

        # UserQuery가 있으면 파이프라인 진행
        if "user_query" in state:
            return state # -> run_pipeline으로 라우팅됨

        # 예외 상황
        state["response"] = SystemResponse(type="warning", message="오류가 발생했습니다.")
        return "end_turn"

    def node_run_pipeline(self, state: DialogueState) -> DialogueState:
        uq = state.get("user_query")
        if not uq: return state

        try:
            result = self.orchestrator.run(user_query=uq)
        except Exception as e:
            state["response"] = SystemResponse(
                type="error",
                message="분석 중 오류가 발생했습니다.",
                payload={"error": str(e)},
            )
            return state

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

        prompt = self._render_result_message(result.get("validation_summary"))
        final_text = self._call_llm_generation(prompt)

        state["response"] = SystemResponse(
            type="result",
            message=final_text,
            payload=None,
        )
        return state

    def node_handle_decision(self, state: DialogueState) -> DialogueState:
        decision = state.get("user_decision")
        orch = state.get("orchestrator_result")

        if decision == "yes":
            uq = orch.get("user_query") if orch else state.get("user_query")
            result = self.orchestrator.run(user_query=uq)
            state["orchestrator_result"] = result

            prompt = self._render_result_message(result.get("validation_summary"))
            final_text = self._call_llm_generation(prompt)

            state["response"] = SystemResponse(
                type="result",
                message=final_text,
                payload=None,
            )
            return state

        summary = orch.get("validation_summary") if orch else None
        prompt = self._render_result_message(summary)
        final_text = self._call_llm_generation(prompt)

        state["response"] = SystemResponse(
            type="result",
            message=final_text,
            payload={"finalized": True},
        )
        return state

    # -----------------------
    # Router Logic
    # -----------------------
    def route_after_parse(self, state: DialogueState) -> str:
        # 일상 대화, 질문, 경고 등 이미 응답이 생성된 경우
        if state.get("response"):
            return "end_turn" # 수정: ask_clarify -> end_turn (의미 명확화)

        if state.get("user_decision"):
            return "handle_decision"

        if "user_query" in state:
            return "run_pipeline"

        return "end_turn"

    # -----------------------
    # Helpers
    # -----------------------
    def _parse_yes_no(self, text: str) -> str | None:
        text = text.strip().lower()
        if text in {"예", "네", "yes", "y", "응", "어", "진행해"}:
            return "yes"
        if text in {"아니오", "아니요", "no", "n", "아니"}:
            return "no"
        return None

    def _llm_parse_user_text(self, text: str) -> Dict[str, Any] | None:
        """
        [수정됨] intent_type을 추가하여 분석 요청과 일반 대화를 구분
        """
        system_prompt = """
        You are an intelligent assistant for biomedical research.
        Analyze the user's input and extract the intent and entities.

        1. Determine 'intent_type':
           - If the user is asking for biomedical analysis, drug validation, or mechanism research, set "intent_type": "analysis".
           - If the user is just saying hello, asking general questions, or chatting, set "intent_type": "general_chat".

        2. If "intent_type" is "analysis", extract:
           - target: Gene, protein, or drug name.
           - disease: Disease or condition.
           - organ: Specific organ if mentioned.
           - question: The core research question.
           - response: null

        3. If "intent_type" is "general_chat":
           - Set all entities (target, disease, etc.) to null.
           - response: Write a polite and helpful response to the user's input in Korean.

        Return the result as a valid JSON object.

        Example 1:
        Input: "EGFR 폐암 효능 검증해줘"
        JSON: {"intent_type": "analysis", "target": "EGFR", "disease": "Lung Cancer", "question": "Verify efficacy", "response": null}

        Example 2:
        Input: "안녕? 너는 누구니?"
        JSON: {"intent_type": "general_chat", "target": null, "response": "안녕하세요! 저는 바이오메디컬 연구를 돕는 AI 어시스턴트입니다."}
        """
        
        try:
            response = llm_client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"[Parser Error] {e}")
            return None

    def _render_result_message(self, summary: Dict[str, Any] | None) -> str:
        if not summary: return "분석된 결과가 없습니다."
        return self._build_summary_prompt(summary)

    def _build_summary_prompt(self, summary: Dict[str, Any]) -> str:
        n = summary.get("n_claims", 0)
        c = summary.get("n_consistent", 0)
        cf = summary.get("n_conflicting", 0)
        ins = summary.get("n_insufficient", 0)
        
        return f"""
        [Validation Summary]
        - Total Claims: {n}
        - Consistent: {c}
        - Conflicting: {cf}
        - Insufficient: {ins}
        
        Based on these stats, write a professional summary for a researcher in Korean.
        """

    def _render_need_more_message(self, summary: Dict[str, Any] | None, hint: str | None) -> str:
        msg = "현재 확보된 문서로는 명확한 결론을 내리기 어렵습니다."
        if hint: msg += f"\n이유: {hint}"
        msg += "\n\n추가 논문 검색을 진행하시겠습니까? (네/아니오)"
        return msg

    def _call_llm_generation(self, prompt: str) -> str:
        try:
            response = llm_client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful biomedical research assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception:
            return "결과 생성 중 오류가 발생했습니다."