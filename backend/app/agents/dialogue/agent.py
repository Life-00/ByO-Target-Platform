# app/agents/dialogue/agent.py
from __future__ import annotations

import json
import uuid
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END

from app.schemas.message import UserMessage, SystemResponse
from app.schemas.user_query import UserQuery, SearchConstraints
from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.dialogue.state import DialogueState

from app.core.llm import llm_client, DEFAULT_LLM_MODEL


class DialogueAgent:
    """
    DialogueAgent
    - 사용자 메시지 파싱 (LLM 기반: 지식 질문 vs 분석 요청 구분)
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
                "end_turn": END,
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
    def run(self, user_message: UserMessage, session_id: str = None, history: List[Dict] = None) -> SystemResponse:
        state: DialogueState = {
            "user_message": user_message,
            "history": history or []
        }
        final_state = self.graph.invoke(state)
        return final_state["response"]

    # -----------------------
    # Nodes
    # -----------------------
    def node_parse(self, state: DialogueState) -> DialogueState:
        um = state["user_message"]
        text = getattr(um, "text", None) or getattr(um, "message", None) or ""
        history = state.get("history", [])

        # 1. Yes/No 응답 판단
        decision = self._parse_yes_no(text)
        if decision:
            state["user_decision"] = decision
            return state

        # 2. 사용자 질의 파싱 (히스토리 반영)
        parsed = self._llm_parse_user_text(text, history)
        
        if not parsed:
            state["response"] = SystemResponse(
                type="warning",
                message="죄송합니다. 요청을 이해하지 못했습니다.",
                payload=None,
            )
            return state

        # [수정됨] 일반 대화/지식 질문 처리
        # intent_type이 'general_chat'이면, 파이프라인을 타지 않고 바로 LLM의 답변을 반환
        if parsed.get("intent_type") == "general_chat":
            chat_response = parsed.get("response") or "네, 무엇을 도와드릴까요?"
            state["response"] = SystemResponse(
                type="chat", 
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
        if state.get("response"): return state
        if state.get("user_decision"): return state

        uq = state.get("user_query")
        if not uq:
            state["response"] = SystemResponse(
                type="warning",
                message="요청을 해석하는 데 실패했습니다. 다시 시도해 주세요.",
                payload=None,
            )
            return state
        return state

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
        if state.get("response"): return "end_turn"
        if state.get("user_decision"): return "handle_decision"
        if "user_query" in state: return "run_pipeline"
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

    def _llm_parse_user_text(self, text: str, history: List[Dict]) -> Dict[str, Any] | None:
        """
        LLM Parser 개선: 단순 질문(QA)과 분석 요청(Analysis)을 명확히 구분
        """
        recent_history = history[-5:] if history else []
        history_text = json.dumps(recent_history, ensure_ascii=False)

        system_prompt = f"""
        You are an intelligent assistant for biomedical research.
        Analyze the user's input and extract the intent and entities.
        
        **Conversation History:**
        {history_text}
        
        **Instructions:**
        1. Consider the 'Conversation History' to resolve context.
        
        2. Determine 'intent_type':
           - "analysis": ONLY if the user explicitly asks to *verify*, *validate*, *analyze papers*, or *check evidence* for a specific hypothesis (e.g., "Verify if Aspirin cures headache", "Find papers on EGFR").
           - "general_chat": If the user asks general knowledge questions (e.g., "What are treatments for Migraine?", "What is EGFR?"), lists, definitions, or casual greetings.

        3. If "intent_type" is "analysis":
           - Extract target, disease, organ, question.
           - response: null

        4. If "intent_type" is "general_chat":
           - Set all entities (target, etc.) to null.
           - response: Provide a helpful, professional answer to the user's question in Korean. (e.g., List the treatments for Migraine).

        Return valid JSON.
        
        Example 1 (General QA):
        Input: "편두통 치료법에는 뭐가 있어?"
        JSON: {{"intent_type": "general_chat", "target": null, "response": "편두통 치료법으로는 약물 치료(트립탄제, 진통제 등)와 비약물 치료(생활습관 교정)가 있습니다..."}}

        Example 2 (Analysis Request):
        Input: "그럼 트립탄제가 편두통에 효과가 있는지 검증해줘"
        JSON: {{"intent_type": "analysis", "target": "Triptans", "disease": "Migraine", "question": "Verify efficacy"}}
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